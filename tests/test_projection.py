from __future__ import annotations

import pytest

from continuum.events import EventLog, EventType
from continuum.models import ApprovalStatus, Origin, StateStatus
from continuum.state.semantic import ProjectionError, project, project_incremental


def started(log: EventLog, run_id: str = "run_1", total: int | None = 100) -> EventLog:
    payload: dict[str, object] = {"goal": "Analyze 100 documents"}
    if total is not None:
        payload["total"] = total
    log.append(run_id, EventType.RUN_STARTED, payload)
    return log


# --- the fold -------------------------------------------------------------- #


def test_run_started_establishes_goal_and_progress() -> None:
    log = started(EventLog())
    state = project("run_1", log.events("run_1"))
    assert state.goal.description == "Analyze 100 documents"
    assert state.goal.version == 1
    assert state.progress.total == 100
    assert state.progress.pending == 100
    assert state.progress.completed == 0


def test_projection_without_a_run_started_event_fails_loudly() -> None:
    log = EventLog()
    log.append("run_1", EventType.TOOL_CALLED, {"tool": "search"})
    with pytest.raises(ProjectionError, match="never recorded RUN_STARTED"):
        project("run_1", log.events("run_1"))


def test_work_completed_advances_progress_and_clears_the_task() -> None:
    log = started(EventLog(), total=10)
    log.append("run_1", EventType.WORK_ADDED, {"task_id": "task_1", "description": "doc 1"})
    log.append("run_1", EventType.WORK_COMPLETED, {"task_id": "task_1"})

    state = project("run_1", log.events("run_1"))
    assert state.progress.completed == 1
    assert state.progress.pending == 9
    assert state.pending_work == []


def test_failed_work_counts_as_failure_not_completion() -> None:
    log = started(EventLog(), total=10)
    log.append("run_1", EventType.WORK_COMPLETED, {"failed": True})
    state = project("run_1", log.events("run_1"))
    assert state.progress.completed == 0
    assert state.progress.failed == 1
    assert state.progress.pending == 9


def test_progress_never_goes_below_zero() -> None:
    log = started(EventLog(), total=None)
    for _ in range(3):
        log.append("run_1", EventType.WORK_COMPLETED, {})
    state = project("run_1", log.events("run_1"))
    assert state.progress.pending == 0
    assert state.progress.completed == 3


def test_decisions_are_recorded_then_invalidated() -> None:
    log = started(EventLog())
    log.append(
        "run_1",
        EventType.DECISION_CREATED,
        {
            "decision_id": "decision_12",
            "decision": "Only include peer-reviewed studies",
            "reason": "User requirement",
            "evidence": ["user_instruction_001"],
        },
    )
    state = project("run_1", log.events("run_1"))
    decision = state.decision("decision_12")
    assert decision is not None
    assert decision.status is StateStatus.VALID
    assert decision.evidence == ["user_instruction_001"]

    log.append(
        "run_1",
        EventType.DECISION_INVALIDATED,
        {"decision_id": "decision_12", "reason": "dataset changed", "status": "stale"},
    )
    state = project("run_1", log.events("run_1"))
    decision = state.decision("decision_12")
    assert decision is not None
    assert decision.status is StateStatus.STALE
    assert decision.invalidated_reason == "dataset changed"
    assert state.valid_decisions() == ()


def test_invalidating_an_unknown_decision_is_an_error() -> None:
    log = started(EventLog())
    log.append("run_1", EventType.DECISION_INVALIDATED, {"decision_id": "nope"})
    with pytest.raises(ProjectionError, match="unknown decision"):
        project("run_1", log.events("run_1"))


def test_repeating_an_id_replaces_rather_than_duplicates() -> None:
    log = started(EventLog())
    for claim in ("first", "second"):
        log.append("run_1", EventType.FINDING_ADDED, {"finding_id": "finding_1", "claim": claim})
    state = project("run_1", log.events("run_1"))
    assert len(state.findings) == 1
    finding = state.finding("finding_1")
    assert finding is not None and finding.claim == "second"


def test_dependencies_and_evidence_are_registered() -> None:
    log = started(EventLog())
    log.append("run_1", EventType.DEPENDENCY_DECLARED, {"resource": "dataset", "version": "v3"})
    log.append("run_1", EventType.EVIDENCE_ADDED, {"evidence_id": "paper_128", "summary": "study"})

    state = project("run_1", log.events("run_1"))
    dependency = state.dependency("dataset")
    assert dependency is not None and dependency.version == "v3"
    assert state.evidence_ids() == {"paper_128"}


def test_approval_lifecycle() -> None:
    log = started(EventLog())
    log.append("run_1", EventType.APPROVAL_REQUESTED, {"approval_id": "ap_1", "subject": "publish"})
    state = project("run_1", log.events("run_1"))
    assert state.approvals[0].status is ApprovalStatus.PENDING

    log.append("run_1", EventType.APPROVAL_GRANTED, {"approval_id": "ap_1", "granted_by": "sam"})
    state = project("run_1", log.events("run_1"))
    assert state.approvals[0].status is ApprovalStatus.GRANTED
    assert state.approvals[0].granted_by == "sam"

    log.append("run_1", EventType.APPROVAL_REVOKED, {"approval_id": "ap_1"})
    state = project("run_1", log.events("run_1"))
    assert state.approvals[0].status is ApprovalStatus.REVOKED


def test_model_change_preserves_recorded_assumptions() -> None:
    log = started(EventLog())
    log.append("run_1", EventType.MODEL_CHANGED, {"model": "model-a", "provider": "local"})
    log.append(
        "run_1",
        EventType.MODEL_ASSUMPTION_RECORDED,
        {"item_id": "msa_1", "description": "relies on model-a tool syntax"},
    )
    log.append("run_1", EventType.MODEL_CHANGED, {"model": "model-b", "provider": "local"})

    state = project("run_1", log.events("run_1"))
    assert state.model is not None
    assert state.model.model == "model-b"
    assert [a.item_id for a in state.model.model_specific_state] == ["msa_1"]


def test_goal_revision_bumps_the_goal_version() -> None:
    log = started(EventLog())
    log.append("run_1", EventType.TASK_UPDATED, {"goal": "Analyze 200 documents"})
    state = project("run_1", log.events("run_1"))
    assert state.goal.description == "Analyze 200 documents"
    assert state.goal.version == 2


# --- properties that recovery depends on ----------------------------------- #


def test_projection_is_reproducible() -> None:
    log = started(EventLog())
    log.append("run_1", EventType.DECISION_CREATED, {"decision_id": "d1", "decision": "x"})
    log.append("run_1", EventType.WORK_COMPLETED, {})

    first = project("run_1", log.events("run_1"))
    second = project("run_1", log.events("run_1"))
    assert first == second


def test_projection_is_prefix_closed() -> None:
    log = started(EventLog(), total=5)
    log.append("run_1", EventType.WORK_COMPLETED, {})
    snapshot_at_2 = project("run_1", log.events("run_1"))
    log.append("run_1", EventType.WORK_COMPLETED, {})

    assert project("run_1", log.events("run_1"), upto=2) == snapshot_at_2
    assert project("run_1", log.events("run_1")).progress.completed == 2


def test_incremental_projection_matches_a_full_reprojection() -> None:
    log = started(EventLog(), total=10)
    log.append("run_1", EventType.WORK_COMPLETED, {})
    partial = project("run_1", log.events("run_1"))

    log.append("run_1", EventType.FINDING_ADDED, {"finding_id": "f1", "claim": "c"})
    log.append("run_1", EventType.WORK_COMPLETED, {})

    incremental, report = project_incremental(
        "run_1", log.events("run_1", after_sequence=partial.source_sequence), base=partial
    )
    full = project("run_1", log.events("run_1"))

    assert incremental == full
    assert report.consumed == 2


def test_source_sequence_tracks_the_consumed_prefix() -> None:
    log = started(EventLog())
    log.append("run_1", EventType.WORK_COMPLETED, {})
    state = project("run_1", log.events("run_1"))
    assert state.source_sequence == log.last_sequence("run_1") == 2


def test_recovery_from_a_partially_trusted_log() -> None:
    """A tampered tail still yields a usable state from the trusted prefix."""
    log = started(EventLog(), total=10)
    log.append("run_1", EventType.WORK_COMPLETED, {})
    log.append("run_1", EventType.WORK_COMPLETED, {})
    log._by_run["run_1"][2] = log._by_run["run_1"][2].model_copy(update={"payload": {"count": 99}})

    report = log.verify("run_1")
    trusted = report.trusted_through["run_1"]
    assert trusted == 2

    state = project("run_1", log.events("run_1"), upto=trusted)
    assert state.progress.completed == 1


# --- ordering and ownership ------------------------------------------------ #


def test_events_from_another_run_are_rejected() -> None:
    log = started(EventLog(), run_id="run_1")
    log.append("run_2", EventType.RUN_STARTED, {"goal": "other"})
    with pytest.raises(ProjectionError, match="belongs to run"):
        project("run_1", log.events("run_2"))


def test_out_of_order_events_are_rejected() -> None:
    log = started(EventLog())
    log.append("run_1", EventType.WORK_COMPLETED, {})
    reversed_events = tuple(reversed(log.events("run_1")))
    with pytest.raises(ProjectionError, match="is not after"):
        project("run_1", reversed_events)


def test_missing_required_payload_fields_are_rejected() -> None:
    log = started(EventLog())
    log.append("run_1", EventType.DECISION_CREATED, {"decision": "no id given"})
    with pytest.raises(ProjectionError, match="missing required field"):
        project("run_1", log.events("run_1"))


# --- forward compatibility -------------------------------------------------- #


def test_non_projecting_events_do_not_change_state() -> None:
    log = started(EventLog())
    before = project("run_1", log.events("run_1"))
    for event_type in (
        EventType.TOOL_CALLED,
        EventType.ACTION_RECORDED,
        EventType.STATE_CHECKPOINTED,
        EventType.RECOVERY_STARTED,
    ):
        log.append("run_1", event_type, {"noise": True})

    after, report = project_incremental("run_1", log.events("run_1"))
    assert after.model_dump(exclude={"source_sequence", "updated_at"}) == before.model_dump(
        exclude={"source_sequence", "updated_at"}
    )
    assert report.complete
    assert report.applied == 1


def test_provenance_points_back_at_the_source_event() -> None:
    log = started(EventLog())
    event = log.append("run_1", EventType.DECISION_CREATED, {"decision_id": "d1", "decision": "x"})
    state = project("run_1", log.events("run_1"))
    decision = state.decision("d1")
    assert decision is not None
    assert decision.provenance.origin is Origin.DETERMINISTIC
    assert decision.provenance.source_event_id == event.event_id
    assert decision.provenance.source_sequence == event.sequence
    assert decision.provenance.reproducible


def test_dangling_evidence_is_detectable() -> None:
    log = started(EventLog())
    log.append(
        "run_1",
        EventType.FINDING_ADDED,
        {"finding_id": "f1", "claim": "c", "evidence": ["paper_404"]},
    )
    state = project("run_1", log.events("run_1"))
    assert state.dangling_evidence() == {"paper_404"}
