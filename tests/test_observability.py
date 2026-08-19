"""Tests for the observability module (metrics collector + Phase 14 dashboard)."""

from __future__ import annotations

from continuum.checkpoint.manager import RestoredRun
from continuum.environment.diff import EnvironmentDiff
from continuum.models import (
    Action,
    ActionStatus,
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
from continuum.observability import (
    CHECKPOINTS_CREATED,
    RECOVERIES_BLOCKED,
    RECOVERIES_RESUMED,
    UNKNOWN_SIDE_EFFECTS,
    VALIDATIONS_RUN,
    Metrics,
    collect_from_decision,
    get_metrics,
    render_dashboard,
    reset_metrics,
    set_metrics,
)
from continuum.recovery.engine import RecoveryDecision
from continuum.recovery.planner import RepairKind, RepairPlan, RepairStep
from continuum.state.validator import ValidationOutcome


def _decision(can_resume: bool, uncertain: tuple[Action, ...] = ()) -> RecoveryDecision:
    """Build a minimal RecoveryDecision for dashboard/metrics tests."""
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
        uncertain_actions=uncertain,
        rationale=("dataset version drift",),
    )


def test_metrics_counter_is_monotonic_and_rejects_negative() -> None:
    m = Metrics()
    m.increment(CHECKPOINTS_CREATED, 3)
    m.increment(CHECKPOINTS_CREATED)
    assert m.counters[CHECKPOINTS_CREATED] == 4
    try:
        m.increment(CHECKPOINTS_CREATED, -1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative increment should raise")


def test_metrics_timer_accumulates() -> None:
    m = Metrics()
    with m.timer("validate"):
        pass
    assert "validate" in m.timers
    assert m.timers["validate"] >= 0.0


def test_get_metrics_returns_active_collector() -> None:
    reset_metrics()
    before = get_metrics()
    token = set_metrics(Metrics())
    try:
        assert get_metrics() is not before
    finally:
        token.var.reset(token)


def test_collect_from_decision_counts_resumed() -> None:
    reset_metrics()
    collect_from_decision(_decision(can_resume=True))
    snap = get_metrics().snapshot()
    assert snap["counters"][VALIDATIONS_RUN] == 1
    assert snap["counters"][RECOVERIES_RESUMED] == 1
    assert snap["counters"].get(RECOVERIES_BLOCKED, 0) == 0
    assert snap["gauges"]["validation.invalid"] == 1


def test_collect_from_decision_counts_blocked_and_unknown() -> None:
    reset_metrics()
    action = Action(run_id="run_x", action_type="github.create_issue", status=ActionStatus.UNKNOWN)
    collect_from_decision(_decision(can_resume=False, uncertain=(action,)))
    snap = get_metrics().snapshot()
    assert snap["counters"][RECOVERIES_BLOCKED] == 1
    assert snap["counters"][UNKNOWN_SIDE_EFFECTS] == 1


def test_render_dashboard_contains_state_components_and_plan() -> None:
    out = render_dashboard(_decision(can_resume=False))
    assert "CONTINUUM RECOVERY DASHBOARD" in out
    assert "run_x" in out
    assert "external dependency dataset: conflicted" in out
    assert "REPAIRS REQUIRED" in out
    assert "revalidate_dependency dataset" in out
    assert "RATIONALE" in out


def test_render_dashboard_marks_resume() -> None:
    out = render_dashboard(_decision(can_resume=True))
    assert "safe to resume:     yes" in out
