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

from collections.abc import Iterable, Mapping
from typing import Any

from continuum.security.hashing import stable_hash

__all__ = ["idempotency_key", "arguments_hash", "IdempotencyKey"]


class IdempotencyKey(str):
    """A content-derived identity for an action attempt.

    A plain string subclass so it serializes and compares transparently, but
    distinct in type signatures where the distinction matters.
    """

    __slots__ = ()


def _strip_volatile(arguments: Mapping[str, Any], volatile: Iterable[str]) -> dict[str, Any]:
    excluded = set(volatile)
    return {k: v for k, v in arguments.items() if k not in excluded}


def arguments_hash(
    arguments: Mapping[str, Any] | None = None,
    *,
    volatile: Iterable[str] = (),
) -> str:
    """Canonical hash of an action's arguments.

    Key order is irrelevant; values are not. Raises if an argument cannot be
    hashed deterministically, because a key that changes between runs would
    silently disable deduplication.
    """
    return stable_hash(_strip_volatile(arguments or {}, volatile))


def idempotency_key(
    action_type: str,
    arguments: Mapping[str, Any] | None = None,
    *,
    scope: str | None = None,
    volatile: Iterable[str] = (),
) -> IdempotencyKey:
    """Derive a stable key identifying this operation.

    ``scope`` narrows the key, typically to a run, so two runs performing the
    same logical operation do not deduplicate against each other. Omit it for
    effects that must be globally unique regardless of run.
    """
    if not action_type:
        raise ValueError("action_type must be a non-empty string")

    return IdempotencyKey(
        stable_hash(
            {
                "scope": scope,
                "type": action_type,
                "arguments": _strip_volatile(arguments or {}, volatile),
            }
        )
    )
