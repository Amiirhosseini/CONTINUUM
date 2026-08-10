"""Which MCP callers may change a run.

The problem this solves is coexistence, not intrusion. Several agents can be
configured against the same database at once — Kilo, Gemini CLI and Claude Code
have all pointed at this project's ``continuum.db`` simultaneously — and until
now any of them could overwrite another's progress, checkpoint over its state,
or claim its actions. This layer keeps honestly-named agents out of each other's
runs.

It is *not* a security boundary. ``clientInfo`` is asserted by the client during
the initialize handshake and never verified, so a caller that wants to be called
``claude-code`` simply says so. What the transport does guarantee is that the
name is fixed at connection time and injected server-side: a caller cannot
elevate itself mid-session by passing a forged ``clientInfo`` in tool arguments.
That is enough to separate cooperating agents, and not enough to stop a hostile
one — which in any case has direct filesystem access to the database and does
not need the MCP server at all.

Read-only tools stay open
-------------------------

Only mutating tools are gated. ``validate``, ``resume`` and ``list_actions``
cannot alter a run, and their whole value is that anyone can ask "is this safe
to continue?" without first being granted permission. Gating them would also
leave an unlisted caller unable to discover *why* its writes are failing.

The split is driven by the ``read_only_hint`` annotation each tool already
declares, rather than a second hand-maintained list that could drift out of
step with it.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

__all__ = [
    "AuthorizationPolicy",
    "NotAuthorized",
    "UnknownCaller",
    "POLICY_ENV_VAR",
    "POLICY_FILENAME",
    "load_policy",
]

POLICY_ENV_VAR = "CONTINUUM_MCP_ALLOW"
POLICY_FILENAME = ".continuum/mcp-policy.json"

#: Used when the handshake supplied no client name at all.
UNKNOWN_CALLER = "<unidentified>"


class NotAuthorized(PermissionError):
    """A caller attempted a mutating tool it is not permitted to use."""


class UnknownCaller(NotAuthorized):
    """The connection never identified itself, so nothing can be authorized."""


class AuthorizationPolicy:
    """Decides whether a named caller may invoke a mutating tool.

    Deny by default. An unlisted caller is not a caller we have decided to
    trust — it is one nobody has made a decision about, and treating an absent
    decision as approval is how the whole point of the layer gets lost. This
    mirrors the validator's stance elsewhere in CONTINUUM: uncertainty degrades
    rather than resolving in its own favour.
    """

    __slots__ = ("allowed", "source")

    def __init__(self, allowed: Iterable[str] = (), *, source: str = "default") -> None:
        self.allowed = frozenset(n.strip() for n in allowed if n and n.strip())
        self.source = source

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        listed = ", ".join(sorted(self.allowed)) or "(none)"
        return f"AuthorizationPolicy(allowed=[{listed}], source={self.source!r})"

    @property
    def denies_everything(self) -> bool:
        return not self.allowed

    def permits(self, caller: str | None) -> bool:
        """Whether ``caller`` may invoke mutating tools."""
        if not caller:
            return False
        return caller in self.allowed

    def require(self, caller: str | None, tool: str) -> None:
        """Raise unless ``caller`` may invoke the mutating tool ``tool``."""
        if caller:
            if caller in self.allowed:
                return
            raise NotAuthorized(
                f"caller {caller!r} is not permitted to use the mutating tool "
                f"{tool!r}. {self._remedy(caller)}"
            )
        raise UnknownCaller(
            f"the connection did not identify itself, so the mutating tool "
            f"{tool!r} is refused. {self._remedy(None)}"
        )

    def _remedy(self, caller: str | None) -> str:
        name = caller or "<your-client-name>"
        if self.denies_everything:
            base = "No callers are currently permitted to make changes."
        else:
            base = f"Permitted callers: {', '.join(sorted(self.allowed))}."
        return (
            f"{base} Read-only tools remain available. To grant access, set "
            f"{POLICY_ENV_VAR}={name!r} or add it to {POLICY_FILENAME}."
        )


def _from_env(value: str | None) -> list[str]:
    if not value:
        return []
    return [part for part in value.replace(",", " ").split() if part]


def _from_file(path: Path) -> tuple[list[str], str] | None:
    """Read an allowlist from ``path``. Returns ``None`` when absent.

    A malformed policy file raises rather than falling back to the default. A
    file that exists is a deliberate statement of intent; silently ignoring a
    typo in it and denying everything would be baffling, and silently ignoring
    it and *allowing* everything would be dangerous.
    """
    if not path.is_file():
        return None
    try:
        data: Any = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read MCP policy at {path}: {exc}") from exc

    if isinstance(data, list):
        names = data
    elif isinstance(data, Mapping):
        names = data.get("allow", data.get("allowed", []))
    else:
        raise ValueError(
            f'MCP policy at {path} must be a list of client names or an object with an "allow" key'
        )
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        raise ValueError(f"MCP policy at {path}: 'allow' must be a list of strings")
    return list(names), str(path)


def load_policy(
    allow: Iterable[str] | None = None,
    *,
    root: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> AuthorizationPolicy:
    """Resolve the policy: explicit argument, then env var, then file, then deny.

    Each source replaces the ones below it rather than merging, so a caller can
    always see exactly where a grant came from by reading ``policy.source``.
    """
    if allow is not None:
        return AuthorizationPolicy(allow, source="argument")

    environ = os.environ if env is None else env
    from_env = _from_env(environ.get(POLICY_ENV_VAR))
    if from_env:
        return AuthorizationPolicy(from_env, source=POLICY_ENV_VAR)

    base = Path.cwd() if root is None else root
    found = _from_file(base / POLICY_FILENAME)
    if found is not None:
        names, source = found
        return AuthorizationPolicy(names, source=source)

    return AuthorizationPolicy((), source="default (deny)")


def caller_name(context: Any) -> str | None:
    """Extract the client's declared name from an MCP request context.

    Read from the initialize handshake, which the transport injects server-side.
    A caller cannot override it by passing ``clientInfo`` in tool arguments —
    verified by test. It is still only what the client *claims* to be.
    """
    if context is None:
        return None
    try:
        info = context.session.client_params.client_info
    except AttributeError:
        return None
    name = getattr(info, "name", None)
    return str(name) if name else None
