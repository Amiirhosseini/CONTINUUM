"""Deciding whether two action attempts are *the same* action.

An idempotency key answers one question: has this exact operation already been
performed? Get it wrong in one direction and the agent duplicates a side effect;
wrong in the other and it refuses to do legitimate new work.

The key is derived from the action type plus its arguments, canonically hashed —
so argument order never matters, but a changed value always does.

Volatile arguments
------------------

Some arguments differ on every call without changing what the operation *means*:
a retry counter, a client-generated request id, a timestamp. Left in the key
they would defeat deduplication entirely, since every retry would look like a
new action. ``volatile`` names the fields to exclude.

This is a sharp edge, so it is opt-in and explicit. Excluding a field that
genuinely distinguishes two operations would collapse them into one and silently
skip real work — the failure mode is quiet, which makes it worse than the noisy
one. Nothing is excluded by default.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from typing import Any

from continuum.security.hashing import stable_hash

__all__ = [
    "idempotency_key",
    "arguments_hash",
    "identity_tokens",
    "IdempotencyKey",
]


class IdempotencyKey(str):
    """A content-derived identity for an action attempt.

    A plain string subclass so it serializes and compares transparently, but
    distinct in type signatures where the distinction matters.
    """

    __slots__ = ()


def _strip_volatile(arguments: Mapping[str, Any], volatile: Iterable[str]) -> dict[str, Any]:
    excluded = set(volatile)
    return {k: v for k, v in arguments.items() if k not in excluded}


def _canonicalize_paths(value: Any) -> Any:
    """Normalize path-like strings so equivalent spellings hash identically.

    Only values that look like local filesystem paths are touched (they contain
    a separator and are not URLs), and normalization is purely lexical
    (``normpath`` plus ``~`` expansion). It never resolves against the process
    working directory, so the result is deterministic on any machine.
    """
    if isinstance(value, str):
        if "://" not in value and ("/" in value or "\\" in value):
            return os.path.normpath(os.path.expanduser(value))
        return value
    if isinstance(value, Mapping):
        return {k: _canonicalize_paths(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_canonicalize_paths(v) for v in value]
    if isinstance(value, tuple):
        return [_canonicalize_paths(v) for v in value]
    return value


def _strip_and_canonicalize(arguments: Mapping[str, Any] | None, volatile: Iterable[str]) -> Any:
    return _canonicalize_paths(_strip_volatile(arguments or {}, volatile))


def arguments_hash(
    arguments: Mapping[str, Any] | None = None,
    *,
    volatile: Iterable[str] = (),
) -> str:
    """Canonical hash of an action's arguments.

    Key order is irrelevant; values are not. Path-like string values are
    normalized first (``normpath`` + ``~`` expansion), so equivalent spellings
    of the same path hash identically. Raises if an argument cannot be hashed
    deterministically, because a key that changes between runs would silently
    disable deduplication.
    """
    return stable_hash(_strip_and_canonicalize(arguments, volatile))


def idempotency_key(
    action_type: str,
    arguments: Mapping[str, Any] | None = None,
    *,
    scope: str | None = None,
    volatile: Iterable[str] = (),
    key: str | None = None,
) -> IdempotencyKey:
    """Derive a stable key identifying this operation.

    ``scope`` narrows the key, typically to a run, so two runs performing the
    same logical operation do not deduplicate against each other. Omit it for
    effects that must be globally unique regardless of run.

    ``key`` overrides argument hashing entirely, in the style of Stripe's
    ``Idempotency-Key``. Argument hashing assumes identical arguments mean the
    same operation, which is wrong for actions that are legitimately repeated:
    sending the same reminder twice is two sends, not one, and hashing would
    silently drop the second. When the caller knows the operation's identity,
    it should say so rather than encode it by perturbing the arguments.
    """
    if key is not None:
        if not key:
            raise ValueError("explicit idempotency key must be a non-empty string")
        return IdempotencyKey(stable_hash({"scope": scope, "type": action_type, "key": key}))

    if not action_type:
        raise ValueError("action_type must be a non-empty string")

    return IdempotencyKey(
        stable_hash(
            {
                "scope": scope,
                "type": action_type,
                "arguments": _strip_and_canonicalize(arguments, volatile),
            }
        )
    )


_WEAK_TOKENS = frozenset(
    {
        "true",
        "false",
        "null",
        "none",
        "tmp",
        "var",
        "home",
        "user",
        "bin",
        "etc",
        "usr",
        "log",
        "logs",
        "out",
        "in",
        "on",
        "sent",
        "file",
    }
)


def _is_strong_token(token: str) -> bool:
    """A token distinctive enough to identify a resource.

    Weak tokens are pure numbers (a count is not an identity), filler words,
    and anything too short to distinguish one resource from another.
    """
    if len(token) < 3 or token in _WEAK_TOKENS:
        return False
    if token.isdigit():
        return False
    return any(ch.isdigit() for ch in token) or "@" in token or token.count(".") >= 1


def identity_tokens(
    arguments: Mapping[str, Any] | None = None,
    *,
    volatile: Iterable[str] = (),
    external_id: str | None = None,
) -> frozenset[str]:
    """Distinctive resource tokens an operation refers to.

    Used by the ledger's defensive fallback when argument hashing cannot match
    two attempts that describe the same resource differently (field renames,
    path formatting). A token is a scalar string value, plus the basename and
    basename-stem of any path-like value, plus the same for ``external_id``.
    Weak tokens are dropped so the fallback never matches on incidental values
    like counts or status words.
    """
    tokens: set[str] = set()

    def collect(value: Any) -> None:
        if isinstance(value, str):
            tokens.add(value)
            base = os.path.basename(value.rstrip("/\\"))
            stem, _ = os.path.splitext(base)
            if base != value:
                tokens.add(base)
            if stem and stem != base:
                tokens.add(stem)
        elif isinstance(value, Mapping):
            for v in value.values():
                collect(v)
        elif isinstance(value, list):
            for v in value:
                collect(v)

    for v in _strip_volatile(arguments or {}, volatile).values():
        collect(v)
    if external_id:
        collect(external_id)

    return frozenset(t for t in tokens if _is_strong_token(t))
