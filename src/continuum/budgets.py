"""Run-level retry budgets (issue #240).

Agent loops invent retries: a failing upstream gets hammered because the
model re-plans after every failure, and each attempt opens a fresh ledger
slot. RetryGuard (arXiv:2511.23278) shows local retry policies amplify cost;
the fix here is a *run-level budget* evaluated at claim time.

Registries live in `.continuum/budgets.json` (JSON, matching the other
registries):

    {"default_max_attempts": 3,
     "action_types": {"send_invoice": {"max_attempts": 5}}}

`evaluate_budget` counts prior attempts for an action type from the folded
ledger and returns whether another claim may proceed. CONTINUUM never retries
anything itself - it counts and gates - so the enforcement surface stays a
single pure function plus thin wiring at claim sites.

Attempts are counted per idempotency key, not per action type (issue #368). The
limit is still configured per type, because that is the unit an operator thinks
in, but what it caps is repetition of one operation. Counting per type made
distinct work compete for the same allowance: three different recipients each
failing once, with no retry anywhere, exhausted a budget of three and blocked a
fourth that had never been attempted.

Authorization-bound budgets (issue #411) add an optional section keyed by
``(action_type, authorization_id)``, giving one logical authorization a durable
monotonic counter however many fresh idempotency keys get minted for it (epic
#390):

    {"authorization_bound": {"send_invoice":
         {"authz:stripe-cust-1": {"counter": 2, "max_attempts": 5}}}}

Configs written before the section existed load unchanged and read as unbound,
which is exactly today's behaviour. ``get_remaining``, ``increment`` and
``would_refuse`` read and maintain entries purely; ``save_budgets`` persists
them. Nothing gates on the section yet (that wiring lands with issue #413).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

__all__ = [
    "DEFAULT_BUDGETS_PATH",
    "AUTHORIZATION_BOUND_KEY",
    "attempts_by_key",
    "attempts_for_type",
    "BudgetConfigError",
    "load_budgets",
    "save_budgets",
    "evaluate_budget",
    "backoff_delay",
    "get_remaining",
    "increment",
    "would_refuse",
]

DEFAULT_BUDGETS_PATH = ".continuum/budgets.json"

#: Registry key of the optional section keyed by (action_type, authorization_id).
AUTHORIZATION_BOUND_KEY = "authorization_bound"

#: Fallback when neither the action type nor the registry sets a limit.
FALLBACK_MAX_ATTEMPTS = 3


class BudgetConfigError(ValueError):
    """The budget registry exists but cannot be honoured."""


def load_budgets(path: Path) -> dict[str, Any]:
    """Read the budget registry. ``{}`` when absent; raise when malformed."""
    if not path.exists():
        return {}
    # Absolute, so the message names a file the operator can open: the
    # relative form depends on the cwd of whatever loaded the registry
    # (a hook, the sidecar, a CI step). Matches gate.py per #333.
    location = path.resolve()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BudgetConfigError(f"{location} is not valid JSON ({exc})") from exc
    if not isinstance(raw, dict):
        raise BudgetConfigError(f"{location}: expected a JSON object")
    action_types = raw.get("action_types", {})
    if not isinstance(action_types, dict):
        raise BudgetConfigError(f"{location}: 'action_types' must be an object")
    for name, spec in action_types.items():
        entry = (
            spec
            if isinstance(spec, int)
            else (spec.get("max_attempts") if isinstance(spec, dict) else None)
        )
        if not isinstance(entry, int) or entry < 1:
            raise BudgetConfigError(
                f"{path}: action type {name!r} needs a positive integer 'max_attempts'"
            )
    default_max = raw.get("default_max_attempts")
    if default_max is not None and (not isinstance(default_max, int) or default_max < 1):
        raise BudgetConfigError(f"{location}: 'default_max_attempts' must be >= 1")
    _validate_authorization_bound(raw, location)
    return raw


def _max_for(action_type: str, raw: Mapping[str, Any]) -> int:
    per_type = raw.get("action_types", {})
    spec = per_type.get(action_type)
    if isinstance(spec, int):
        return spec
    if isinstance(spec, dict) and isinstance(spec.get("max_attempts"), int):
        return int(spec["max_attempts"])
    fallback = raw.get("default_max_attempts", FALLBACK_MAX_ATTEMPTS)
    return int(fallback)


def attempts_by_key(events: Any, action_type: str) -> dict[str, int]:
    """Unsettled claim attempts for ``action_type``, counted per idempotency key.

    A retry budget has to count retries of *one operation*. Counting per action
    type instead conflated distinct work with repetition: three different
    recipients each failing once, with no retry anywhere, exhausted a budget of
    three and blocked a fourth recipient that had never been attempted (issue
    #368). Any fan-out with more than ``max_attempts`` failures of one type
    deadlocked mid-run.

    The key is the right unit because it *is* the operation's identity, and it is
    stable across retries: re-claiming after FAILED or COMPENSATED copies the
    existing action, so successive attempts under one key accumulate here rather
    than each opening a fresh row.

    A claim slot (an ``ACTION_RECORDED`` whose action status is STARTED) is one
    attempt. Settlement events are updates, not new attempts, so retries count but
    their bookkeeping does not. Keys whose action went on to COMPLETE are omitted:
    an operation that succeeded was never retried (issue #309).
    """
    from continuum.events import EventType
    from continuum.models import ActionStatus

    slots: dict[str, int] = {}
    final: dict[str, str] = {}
    for event in events:
        if event.type is not EventType.ACTION_RECORDED:
            continue
        action = event.payload.get("action")
        if not isinstance(action, Mapping) or action.get("action_type") != action_type:
            continue
        key = str(event.payload.get("key", ""))
        if not key:
            continue
        status = str(action.get("status"))
        if status == ActionStatus.STARTED.value:
            slots[key] = slots.get(key, 0) + 1
        final[key] = status

    return {
        key: count for key, count in slots.items() if final.get(key) != ActionStatus.COMPLETED.value
    }


def attempts_for_type(events: Any, action_type: str) -> int:
    """The most attempts any single operation of ``action_type`` has used.

    Reports the figure the budget is actually compared against, so the ``continuum
    budget`` view agrees with what the claim site enforces. It is deliberately not
    the sum across keys: that total is a measure of how much distinct work a run
    did, which no limit here caps (issue #368).
    """
    per_key = attempts_by_key(events, action_type)
    return max(per_key.values(), default=0)


def evaluate_budget(
    raw_config: Mapping[str, Any] | None,
    action_type: str,
    attempts_so_far: int,
) -> tuple[bool, int, int]:
    """Return ``(allowed, attempts_so_far, max_attempts)``.

    Pure so claim sites can call it with nothing but the folded attempt count.
    """
    _ = raw_config  # kept in signature for symmetry with other registries
    cfg = raw_config or {}
    maximum = _max_for(action_type, cfg)
    return attempts_so_far < maximum, attempts_so_far, maximum


def backoff_delay(
    attempt: int,
    *,
    base: float = 1.0,
    cap: float = 60.0,
) -> float:
    """Exponential backoff with a ceiling. Pure; jitter is the caller's job."""
    if attempt < 1:
        raise ValueError(f"attempt must be >= 1, got {attempt}")
    return float(min(base * (2 ** (attempt - 1)), cap))


# --- authorization-bound budgets (issue #411) --------------------------------------- #


def _validate_authorization_bound(raw: Mapping[str, Any], location: Path) -> None:
    """Shape-check the optional authorization-bound section of a loaded registry.

    Absent means unbound, which is valid: configs without authorization data
    must keep loading exactly as they always did (epic #390).
    """
    section = raw.get(AUTHORIZATION_BOUND_KEY)
    if section is None:
        return
    if not isinstance(section, dict):
        raise BudgetConfigError(f"{location}: '{AUTHORIZATION_BOUND_KEY}' must be an object")
    for action_type, entries in section.items():
        if not isinstance(entries, dict):
            raise BudgetConfigError(
                f"{location}: authorization-bound entries for {action_type!r} must be an object"
            )
        for authorization_id, entry in entries.items():
            label = f"{location}: authorization-bound entry {action_type!r}/{authorization_id!r}"
            if not isinstance(entry, dict):
                raise BudgetConfigError(f"{label} must be an object")
            counter = entry.get("counter", 0)
            if not isinstance(counter, int) or counter < 0:
                raise BudgetConfigError(f"{label} needs a non-negative integer 'counter'")
            max_attempts = entry.get("max_attempts")
            if not isinstance(max_attempts, int) or max_attempts < 1:
                raise BudgetConfigError(f"{label} needs a positive integer 'max_attempts'")


def save_budgets(path: Path, data: Mapping[str, Any]) -> None:
    """Write ``data`` back to the registry as readable JSON.

    Insertion order is preserved so editing one entry does not churn the whole
    file, and the trailing newline matches how hand-maintained registries end.
    Keys the loader does not know pass through untouched, exactly as when the
    file is edited by hand.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _bound_entry(
    raw: Mapping[str, Any],
    action_type: str,
    authorization_id: str,
) -> dict[str, Any]:
    """The registry's entry for one authorization; KeyError names a missing one."""
    section = raw.get(AUTHORIZATION_BOUND_KEY)
    entries = section.get(action_type, {}) if isinstance(section, dict) else {}
    entry = entries.get(authorization_id) if isinstance(entries, dict) else None
    if not isinstance(entry, dict):
        raise KeyError(f"no authorization-bound budget for {action_type!r} / {authorization_id!r}")
    return entry


def get_remaining(
    raw: Mapping[str, Any],
    action_type: str,
    authorization_id: str,
) -> int | None:
    """Attempts still available to this authorization, or ``None`` when unbound.

    Pure: it reads only the mapping :func:`load_budgets` returned. An absent
    section reads as unbound, which keeps runs without authorization data on
    today's behaviour (epic #390).
    """
    try:
        entry = _bound_entry(raw, action_type, authorization_id)
    except KeyError:
        return None
    used = int(entry.get("counter", 0))
    return max(0, int(entry["max_attempts"]) - used)


def increment(
    raw: Mapping[str, Any],
    action_type: str,
    authorization_id: str,
) -> int:
    """Count one more attempt against the authorization, return what remains.

    Mutates ``raw`` in place; the counter only ever climbs, and persisting the
    change is the caller's job (:func:`save_budgets`). An authorization the
    registry does not know raises KeyError rather than receiving an invented
    cap, because guessing a limit the operator never set is how budgets stop
    meaning anything.
    """
    entry = _bound_entry(raw, action_type, authorization_id)
    entry["counter"] = int(entry.get("counter", 0)) + 1
    return max(0, int(entry["max_attempts"]) - int(entry["counter"]))


def would_refuse(
    raw: Mapping[str, Any],
    action_type: str,
    authorization_id: str,
) -> tuple[bool, str]:
    """Whether one more attempt under this authorization would be refused.

    Returns ``(refused, reason)``. Unbound authorizations never refuse here,
    matching today's behaviour; exhausted ones refuse with a reason naming the
    action type, the authorization id and both figures, so a caller can say
    exactly what ran out.
    """
    label = f"{action_type!r} / {authorization_id!r}"
    try:
        entry = _bound_entry(raw, action_type, authorization_id)
    except KeyError:
        return False, f"no authorization-bound budget for {label}"
    used = int(entry.get("counter", 0))
    maximum = int(entry["max_attempts"])
    if used >= maximum:
        detail = f"{label} exhausted its authorization-bound budget"
        return True, f"{detail} ({used} of {maximum} attempts used)"
    return False, f"{label} has {maximum - used} of {maximum} attempts remaining"
