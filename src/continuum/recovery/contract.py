"""The recovery contract.

A contract is the machine-readable answer to "what am I allowed to do now?".
It names what was verified, what was invalidated, what must happen before
normal work resumes, and — critically — the *single* next permitted action.

One action, not a set. If a contract listed everything currently allowed, an
agent could pick the convenient one and skip reconciling the side effect it was
supposed to resolve first. Naming exactly one step makes the gate enforceable
and the ordering meaningful.

Contracts are deterministic: the same state, environment and ledger always
produce a byte-identical contract. That is what makes them auditable, diffable
and safe to compare in tests. They are sealed with an integrity hash for the
same reason checkpoints are — a contract that could be edited between issue and
enforcement would gate nothing.
"""

from __future__ import annotations

from continuum.models import (
    Component,
    RecoveryContract,
    RecoverySafety,
    StateStatus,
    utcnow,
)
from continuum.recovery.planner import RepairPlan
from continuum.security.hashing import stable_hash
from continuum.state.validator import ValidationOutcome

__all__ = ["build_contract", "seal_contract", "verify_contract"]


def _identifier(component: Component, component_id: str | None) -> str:
    return f"{component.value}:{component_id}" if component_id else component.value


def seal_contract(contract: RecoveryContract) -> RecoveryContract:
    """Attach an integrity hash covering the contract's terms."""
    payload = contract.model_dump(mode="json", exclude={"integrity_hash", "created_at"})
    return contract.model_copy(update={"integrity_hash": stable_hash(payload)})


def verify_contract(contract: RecoveryContract) -> bool:
    """Whether a contract still matches the terms it was sealed with."""
    if contract.integrity_hash is None:
        return False
    payload = contract.model_dump(mode="json", exclude={"integrity_hash", "created_at"})
    return contract.integrity_hash == stable_hash(payload)


def build_contract(
    *,
    run_id: str,
    checkpoint_version: int,
    safety: RecoverySafety,
    validation: ValidationOutcome,
    plan: RepairPlan,
) -> RecoveryContract:
    """Assemble a sealed, deterministic contract.

    ``verified`` and ``invalidated`` are sorted so two runs over equivalent
    state produce identical contracts regardless of dictionary iteration order.
    """
    verified: list[str] = []
    invalidated: list[str] = []

    for entry in validation.report.statuses:
        name = _identifier(entry.component, entry.component_id)
        if entry.status is StateStatus.VALID:
            verified.append(name)
        else:
            invalidated.append(f"{name} ({entry.status.value})")

    next_action = plan.first.action_name if plan.first else None

    contract = RecoveryContract(
        run_id=run_id,
        checkpoint_version=checkpoint_version,
        recovery_status=safety,
        verified=sorted(verified),
        invalidated=sorted(invalidated),
        required_actions=[step.action_name for step in plan.steps],
        next_allowed_action=next_action,
        created_at=utcnow(),
    )
    return seal_contract(contract)


def render_contract(contract: RecoveryContract) -> str:
    """Human-readable rendering of a contract."""
    lines = [
        f"run_id:            {contract.run_id}",
        f"checkpoint:        v{contract.checkpoint_version}",
        f"recovery_status:   {contract.recovery_status.value}",
    ]
    if contract.verified:
        lines.append(f"verified:          {', '.join(contract.verified)}")
    if contract.invalidated:
        lines.append(f"invalidated:       {', '.join(contract.invalidated)}")
    if contract.required_actions:
        lines.append("required_actions:")
        lines += [f"  - {a}" for a in contract.required_actions]
    lines.append(f"next_allowed:      {contract.next_allowed_action or 'continue'}")
    return "\n".join(lines)
