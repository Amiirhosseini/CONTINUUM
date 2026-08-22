"""Pre-action gating for external side effects (issue #217).

The two-phase action protocol is only as strong as the model's willingness to
follow it. Observation (#210) records what happened; it cannot stop an
unclaimed side effect from firing. Harnesses that support pre-tool-use hooks
which can *deny* a call make enforcement possible at the host layer, outside
the model's control.

This module holds the pure decision logic so it can be tested exhaustively
without a harness:

- :func:`load_gate_config` reads ``.continuum/gate.json``, which registers
  side-effect tools and the stable-key templates that identify their
  operations.
- :func:`render_key` derives the idempotency key from the call's structured
  arguments using the configured template. Keys come from configuration, never
  from LLM-authored strings.
- :func:`decide` answers one question: may this tool call proceed?

The decision rule mirrors the ledger's semantics exactly. A gated call is
allowed only when a live claim (status ``STARTED``) already exists for its
derived key. Anything else is denied with instructions: unclaimed calls are
told how to claim, completed calls are told the effect already happened (this
is the dedup verdict made physical), uncertain calls are told to reconcile,
and closed attempts are told to claim again. When the config file exists but
is malformed the gate fails closed: a file someone wrote is a statement of
intent, and silently letting everything through would defeat it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from continuum.actions.idempotency import idempotency_key
from continuum.models import ActionStatus

__all__ = [
    "DEFAULT_GATE_CONFIG_PATH",
    "Decision",
    "load_gate_config",
    "render_key",
    "decide",
]

#: Where the gate configuration lives, relative to the project root the hook
#: runs in. JSON, matching the existing ``.continuum/mcp-policy.json``
#: convention.
DEFAULT_GATE_CONFIG_PATH = ".continuum/gate.json"


class GateConfigError(ValueError):
    """The gate configuration exists but cannot be honoured."""


@dataclass(frozen=True)
class Decision:
    """The outcome of one gate evaluation."""

    allow: bool
    reason: str


def load_gate_config(path: Path) -> dict[str, dict[str, Any]] | None:
    """Read the gate registry. Returns None when no configuration exists.

    A missing file means "no gate configured", which is distinct from a file
    that exists and is broken: the latter raises rather than degrading into
    silently passing every call.
    """
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GateConfigError(f"{path} is not valid JSON ({exc})") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("tools", {}), dict):
        raise GateConfigError(f"{path}: expected {{'tools': {{...}}}}")
    tools = raw.get("tools") or {}
    for tool, spec in tools.items():
        if not isinstance(spec, dict) or not isinstance(spec.get("key_template"), str):
            raise GateConfigError(f"{path}: tool {tool!r} needs a string 'key_template'")
        if spec.get("action_type") is not None and not isinstance(spec.get("action_type"), str):
            raise GateConfigError(f"{path}: tool {tool!r} 'action_type' must be a string")
    return tools


def render_key(template: str, tool_input: Mapping[str, Any]) -> str:
    """Substitute ``{field}`` placeholders from the call's arguments.

    Only top-level argument fields are supported in v1. A placeholder with no
    matching argument raises: a template the current call cannot satisfy is a
    configuration problem worth surfacing, not something to paper over with a
    weaker identity.
    """
    import string

    fields = [name for _, name, _, _ in string.Formatter().parse(template) if name]
    missing = [f for f in fields if f not in tool_input]
    if missing:
        raise GateConfigError(
            f"key template {template!r} needs argument(s) {missing} "
            f"but the call supplied {sorted(tool_input)!r}"
        )
    values = {f: tool_input[f] for f in fields}
    return template.format(**values)


def _expected_key(action_type: str, run_id: str, rendered: str) -> str:
    """The exact ledger key a claim of this operation must have produced."""
    return str(idempotency_key(action_type, None, scope=run_id, key=rendered))


def decide(
    config: Mapping[str, Mapping[str, Any]] | None,
    tool_name: str,
    tool_input: Mapping[str, Any],
    *,
    run_id: str,
    actions_by_key: Mapping[str, Any],
) -> Decision:
    """Decide whether one tool call may proceed.

    ``actions_by_key`` maps ledger keys to Action records (the output of
    ``fold_action_events`` over the run's event log). Ungated tools pass
    immediately without touching anything else.
    """
    if config is None:
        return Decision(True, "no gate configured")
    spec = config.get(tool_name)
    if spec is None:
        return Decision(True, "tool is not gated")

    action_type = spec.get("action_type") or tool_name
    try:
        rendered = render_key(spec["key_template"], tool_input)
        key = _expected_key(action_type, run_id, rendered)
    except GateConfigError as exc:
        return Decision(False, f"gate configuration error: {exc}")

    action = actions_by_key.get(key)
    if action is None or action.action_type != action_type:
        return Decision(
            False,
            f"side effect {action_type!r} with key {rendered!r} has no ledger claim. "
            f"Call the MCP tool continuum_intercept_action with run_id={run_id!r}, "
            f"action_type={action_type!r}, key={rendered!r} first, then repeat this call.",
        )

    status = action.status
    if status is ActionStatus.STARTED:
        return Decision(True, f"live claim {rendered!r}")
    if status is ActionStatus.COMPLETED:
        return Decision(
            False,
            f"{action_type!r} with key {rendered!r} was already completed"
            + (f" (external id {action.external_id!r})" if action.external_id else "")
            + ". Do not repeat it.",
        )
    if status is ActionStatus.UNKNOWN:
        return Decision(
            False,
            f"{action_type!r} with key {rendered!r} has an unknown outcome. Call "
            f"continuum_reconcile_action for it before attempting anything further.",
        )
    return Decision(
        False,
        f"the previous attempt of {action_type!r} with key {rendered!r} is closed "
        f"(status {status.value}). Claim it again through continuum_intercept_action "
        f"before retrying.",
    )
