"""Tests for the portable Recovery State interchange schema (roadmap B4)."""

from __future__ import annotations

from continuum.checkpoint.manager import RestoredRun
from continuum.environment.diff import EnvironmentDiff
from continuum.interchange import (
    INTERCHANGE_SCHEMA_VERSION,
    RecoveryInterchange,
    export_decision,
    reconstruct_decision,
)
from continuum.models import (
    Component,
    ComponentValidationEntry,
    Goal,
    RecoveryContract,
    RecoveryMode,
    RecoverySafety,
    SemanticState,
    StateStatus,
    StateValidationResult,
)
from continuum.recovery.engine import RecoveryDecision
from continuum.recovery.planner import RepairKind, RepairPlan, RepairStep
from continuum.state.validator import ValidationOutcome


def _decision(can_resume: bool) -> RecoveryDecision:
    state = SemanticState(run_id="run_x", goal=Goal(description="recover"))
    contract = RecoveryContract(
        run_id="run_x",
        checkpoint_version=3,
        recovery_status=RecoverySafety.SAFE_TO_RESUME if can_resume else RecoverySafety.BLOCKED,
        verified=["goal"],
        invalidated=["external_dependency dataset (CONFLICTED)"],
        required_actions=[],
        next_allowed_action=None,
    )
    plan = RepairPlan(
        steps=[
            RepairStep(
                kind=RepairKind.REVALIDATE_DEPENDENCY,
                target="dataset",
                reason="version drift",
            )
        ]
    )
    validation = ValidationOutcome(
        state=state,
        report=StateValidationResult(
            run_id="run_x",
            checkpoint_version=3,
            statuses=[
                ComponentValidationEntry(component=Component.GOAL, status=StateStatus.VALID),
                ComponentValidationEntry(
                    component=Component.EXTERNAL_DEPENDENCY,
                    component_id="dataset",
                    status=StateStatus.CONFLICTED,
                    detail="v3 vs v4",
                ),
            ],
            safe_to_resume=can_resume,
        ),
        environment_diff=EnvironmentDiff(),
    )
    restored = RestoredRun(
        run_id="run_x", state=state, checkpoint=None, pending_events=0, replayed=True
    )
    return RecoveryDecision(
        run_id="run_x",
        mode=RecoveryMode.RESUME if can_resume else RecoveryMode.WAIT,
        contract=contract,
        plan=plan,
        validation=validation,
        restored=restored,
        uncertain_actions=(),
        rationale=("dataset version drift",),
    )


def test_export_contains_portable_fields() -> None:
    out = export_decision(_decision(can_resume=False))
    assert out.schema_version == INTERCHANGE_SCHEMA_VERSION
    assert out.run_id == "run_x"
    assert out.recovery_mode == "wait"
    assert out.safe is False
    assert out.state["run_id"] == "run_x"
    assert out.contract["checkpoint_version"] == 3
    assert {s.component for s in out.statuses} == {"goal", "external_dependency"}
    assert out.plan_steps[0].action_name == "revalidate_dependency:dataset"
    assert out.rationale == ["dataset version drift"]


def test_json_round_trip_is_stable() -> None:
    original = export_decision(_decision(can_resume=True))
    text = original.to_json()
    restored = RecoveryInterchange.from_json(text)
    assert restored == original


def test_from_json_rejects_unknown_schema_version() -> None:
    payload = export_decision(_decision(can_resume=True)).model_dump()
    payload["schema_version"] = "continuum-recovery/99"
    text = __import__("json").dumps(payload)
    try:
        RecoveryInterchange.from_json(text)
    except ValueError:
        pass
    else:
        raise AssertionError("unknown schema version should be rejected")


def test_reconstruct_yields_equivalent_verdict() -> None:
    decision = _decision(can_resume=False)
    rebuilt = reconstruct_decision(export_decision(decision))
    assert rebuilt.run_id == decision.run_id
    assert rebuilt.mode is RecoveryMode.WAIT
    assert rebuilt.safe == decision.safe
    assert rebuilt.contract.checkpoint_version == decision.contract.checkpoint_version
    assert {e.component for e in rebuilt.validation.report.statuses} == {
        Component.GOAL,
        Component.EXTERNAL_DEPENDENCY,
    }
    assert rebuilt.plan.steps[0].action_name == "revalidate_dependency:dataset"
