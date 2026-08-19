"""Portable Recovery State interchange schema (roadmap item B4).

CONTINUUM's recovery verdict (the :class:`~continuum.recovery.engine.RecoveryDecision`)
is the artifact an external tool should be able to verify: it says what was
verified, what was invalidated, and the single next permitted action. This
module serialises that verdict to a stable, versioned JSON schema so different
systems and versions can interoperate and outside verifiers can check CONTINUUM
output without importing the library.

The schema is intentionally a small, explicit projection of public models
(rather than a raw ``model_dump`` of internal dataclasses) so it stays stable
across internal refactors.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from continuum.checkpoint.manager import RestoredRun
from continuum.environment.diff import EnvironmentDiff
from continuum.models import (
    Component,
    ComponentValidationEntry,
    RecoveryContract,
    RecoveryMode,
    SemanticState,
    StateStatus,
    StateValidationResult,
    utcnow,
)
from continuum.recovery.engine import RecoveryDecision
from continuum.recovery.planner import RepairKind, RepairPlan, RepairStep
from continuum.state.validator import ValidationOutcome

__all__ = [
    "INTERCHANGE_SCHEMA_VERSION",
    "InterchangeStatus",
    "InterchangeStep",
    "RecoveryInterchange",
    "export_decision",
    "reconstruct_decision",
]


INTERCHANGE_SCHEMA_VERSION = "continuum-recovery/1"


class InterchangeStatus(BaseModel):
    """One validated component, portable form."""

    model_config = ConfigDict(frozen=True)

    component: str
    component_id: str | None = None
    status: str
    detail: str = ""


class InterchangeStep(BaseModel):
    """One repair step, portable form."""

    model_config = ConfigDict(frozen=True)

    kind: str
    target: str
    reason: str = ""
    blocking: bool = True
    requires_human: bool = False
    action_name: str


class RecoveryInterchange(BaseModel):
    """A versioned, externally-verifiable snapshot of a recovery verdict."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = INTERCHANGE_SCHEMA_VERSION
    run_id: str
    checkpoint_version: int
    recovery_mode: str
    safe: bool
    generated_at: str
    state: dict[str, Any]
    contract: dict[str, Any]
    statuses: list[InterchangeStatus] = []
    plan_steps: list[InterchangeStep] = []
    rationale: list[str] = []
    integrity_hash: str | None = None

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, text: str) -> RecoveryInterchange:
        obj = cls.model_validate_json(text)
        if obj.schema_version != INTERCHANGE_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported interchange schema version: {obj.schema_version!r} "
                f"(expected {INTERCHANGE_SCHEMA_VERSION!r})"
            )
        return obj


def export_decision(decision: RecoveryDecision) -> RecoveryInterchange:
    """Project a recovery verdict into the portable interchange schema."""
    contract = decision.contract
    return RecoveryInterchange(
        run_id=decision.run_id,
        checkpoint_version=contract.checkpoint_version,
        recovery_mode=decision.mode.value,
        safe=decision.safe,
        generated_at=utcnow().isoformat(),
        state=decision.validation.state.model_dump(mode="json"),
        contract=contract.model_dump(mode="json"),
        statuses=[
            InterchangeStatus(
                component=entry.component.value,
                component_id=entry.component_id,
                status=entry.status.value,
                detail=entry.detail,
            )
            for entry in decision.validation.report.statuses
        ],
        plan_steps=[
            InterchangeStep(
                kind=step.kind.value,
                target=step.target,
                reason=step.reason,
                blocking=step.blocking,
                requires_human=step.requires_human,
                action_name=step.action_name,
            )
            for step in decision.plan.steps
        ],
        rationale=list(decision.rationale),
        integrity_hash=contract.integrity_hash,
    )


def reconstruct_decision(interchange: RecoveryInterchange) -> RecoveryDecision:
    """Rebuild a usable :class:`RecoveryDecision` from portable data.

    Used when one system's verdict is imported by another. Round-trips the
    fields that external tools care about; the rebuilt verdict is equivalent for
    verification purposes even though it carries no live storage handle.
    """
    state = SemanticState.model_validate(interchange.state)
    contract = RecoveryContract.model_validate(interchange.contract)
    report = StateValidationResult(
        run_id=interchange.run_id,
        checkpoint_version=interchange.checkpoint_version,
        statuses=[
            ComponentValidationEntry(
                component=Component(s.component),
                component_id=s.component_id,
                status=StateStatus(s.status),
                detail=s.detail,
            )
            for s in interchange.statuses
        ],
        safe_to_resume=interchange.safe,
        recovery_mode=RecoveryMode(interchange.recovery_mode),
        validated_at=utcnow(),
    )
    validation = ValidationOutcome(
        state=state,
        report=report,
        environment_diff=EnvironmentDiff(),
    )
    plan = RepairPlan(
        steps=[
            RepairStep(
                kind=RepairKind(s.kind),
                target=s.target,
                reason=s.reason,
                blocking=s.blocking,
                requires_human=s.requires_human,
            )
            for s in interchange.plan_steps
        ]
    )
    restored = RestoredRun(
        run_id=interchange.run_id,
        state=state,
        checkpoint=None,
        pending_events=0,
        replayed=False,
    )
    return RecoveryDecision(
        run_id=interchange.run_id,
        mode=RecoveryMode(interchange.recovery_mode),
        contract=contract,
        plan=plan,
        validation=validation,
        restored=restored,
        uncertain_actions=(),
        rationale=tuple(interchange.rationale),
    )
