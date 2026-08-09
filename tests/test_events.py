from __future__ import annotations

import pytest
from pydantic import ValidationError

from continuum.events import (
    AppendOnlyViolation,
    Event,
    EventLog,
    EventType,
)


def seed(log: EventLog, run_id: str = "run_1", count: int = 3) -> None:
    log.append(run_id, EventType.RUN_STARTED, {"goal": "analyze"})
    for i in range(count - 1):
        log.append(run_id, EventType.TOOL_CALLED, {"tool": "search", "i": i})


# --- append semantics ------------------------------------------------------ #


def test_sequences_start_at_one_and_increment() -> None:
    log = EventLog()
    seed(log, count=3)
    assert [e.sequence for e in log.events("run_1")] == [1, 2, 3]


def test_sequences_are_independent_per_run() -> None:
    log = EventLog()
    log.append("run_a", EventType.RUN_STARTED)
    log.append("run_b", EventType.RUN_STARTED)
    log.append("run_a", EventType.TASK_UPDATED)
    assert [e.sequence for e in log.events("run_a")] == [1, 2]
    assert [e.sequence for e in log.events("run_b")] == [1]
    assert log.last_sequence("run_a") == 2
    assert log.last_sequence("unknown_run") == 0


def test_events_are_immutable() -> None:
    log = EventLog()
    event = log.append("run_1", EventType.RUN_STARTED)
    with pytest.raises(ValidationError):
        event.sequence = 99  # type: ignore[misc]


def test_returned_views_are_snapshots_not_live_handles() -> None:
    log = EventLog()
    seed(log, count=2)
    view = log.events("run_1")
    log.append("run_1", EventType.TASK_UPDATED)
    assert len(view) == 2
    assert len(log.events("run_1")) == 3


def test_events_can_be_filtered_by_type_and_cursor() -> None:
    log = EventLog()
    seed(log, count=4)
    assert len(log.by_type("run_1", EventType.TOOL_CALLED)) == 3
    assert len(log.by_type("run_1", EventType.RUN_STARTED)) == 1
    assert [e.sequence for e in log.events("run_1", after_sequence=2)] == [3, 4]


def test_log_reports_head_and_size() -> None:
    log = EventLog()
    assert log.head("run_1") is None
    seed(log, count=3)
    log.append("run_2", EventType.RUN_STARTED)
    head = log.head("run_1")
    assert head is not None and head.sequence == 3
    assert len(log) == 4
    assert set(log.runs()) == {"run_1", "run_2"}
    assert len(list(log)) == 4


def test_payload_is_copied_so_caller_mutation_cannot_rewrite_history() -> None:
    log = EventLog()
    payload = {"tool": "search"}
    event = log.append("run_1", EventType.TOOL_CALLED, payload)
    payload["tool"] = "delete_everything"
    assert event.payload["tool"] == "search"
    assert log.verify().ok


# --- hash chain ------------------------------------------------------------ #


def test_first_event_has_no_predecessor() -> None:
    log = EventLog()
    first = log.append("run_1", EventType.RUN_STARTED)
    assert first.prev_hash is None
    assert first.hash == first.digest()


def test_each_event_links_to_the_previous_hash() -> None:
    log = EventLog()
    seed(log, count=4)
    events = log.events("run_1")
    for previous, current in zip(events, events[1:], strict=False):
        assert current.prev_hash == previous.hash
        assert current.prev_hash == previous.digest()


def test_identical_content_in_different_positions_hashes_differently() -> None:
    log = EventLog()
    a = log.append("run_1", EventType.TOOL_CALLED, {"tool": "search"}, event_id="event_fixed")
    b = log.append("run_1", EventType.TOOL_CALLED, {"tool": "search"}, event_id="event_fixed")
    assert a.hash != b.hash


def test_verify_passes_on_a_clean_log() -> None:
    log = EventLog()
    seed(log, "run_1", 5)
    seed(log, "run_2", 3)
    report = log.verify()
    assert report.ok
    assert report.checked == 8
    assert report.violations == []


def test_verify_detects_edited_payload() -> None:
    log = EventLog()
    seed(log, count=3)
    tampered = log._by_run["run_1"][1].model_copy(update={"payload": {"tool": "rm -rf"}})
    log._by_run["run_1"][1] = tampered

    report = log.verify("run_1")
    assert not report.ok
    kinds = {v.kind for v in report.violations}
    assert "TAMPERED_CONTENT" in kinds
    # the edit also invalidates every later event: the chain propagates digests
    assert "BROKEN_CHAIN" in kinds
    assert report.trusted_through["run_1"] == 1


def test_verify_detects_a_deleted_event() -> None:
    log = EventLog()
    seed(log, count=4)
    del log._by_run["run_1"][1]

    report = log.verify("run_1")
    assert not report.ok
    assert {v.kind for v in report.violations} >= {"SEQUENCE_GAP", "BROKEN_CHAIN"}
    assert report.trusted_through["run_1"] == 1


def test_verify_reports_a_trusted_prefix_for_clean_runs() -> None:
    log = EventLog()
    seed(log, "run_1", 5)
    assert log.verify("run_1").trusted_through == {"run_1": 5}
    assert log.verify("empty_run").trusted_through == {"empty_run": 0}


def test_tampering_the_last_event_keeps_the_earlier_prefix_trusted() -> None:
    log = EventLog()
    seed(log, count=4)
    log._by_run["run_1"][3] = log._by_run["run_1"][3].model_copy(update={"payload": {"x": 1}})

    report = log.verify("run_1")
    assert not report.ok
    assert report.trusted_through["run_1"] == 3


def test_damage_is_localised_not_flooded() -> None:
    """One edit reports on the event and its successor, then the walk re-syncs."""
    log = EventLog()
    seed(log, count=20)
    log._by_run["run_1"][4] = log._by_run["run_1"][4].model_copy(update={"payload": {"x": 1}})

    report = log.verify("run_1")
    assert not report.ok
    assert {v.sequence for v in report.violations} == {5, 6}
    assert report.trusted_through["run_1"] == 4


def test_violation_collection_is_capped() -> None:
    log = EventLog()
    seed(log, count=30)
    for index in (0, 5, 11):
        log._by_run["run_1"][index] = log._by_run["run_1"][index].model_copy(
            update={"payload": {"x": index}}
        )

    report = log.verify("run_1", max_violations=3)
    assert not report.ok
    assert report.truncated
    assert len(report.violations) == 3


def test_verify_scopes_violations_to_the_damaged_run() -> None:
    log = EventLog()
    seed(log, "run_good", 3)
    seed(log, "run_bad", 3)
    del log._by_run["run_bad"][0]

    assert log.verify("run_good").ok
    assert not log.verify("run_bad").ok
    assert not log.verify().ok


# --- reloading from storage ------------------------------------------------ #


def test_sealed_events_can_be_reloaded() -> None:
    source = EventLog()
    seed(source, "run_1", 3)
    serialized = [e.model_dump_json() for e in source.events("run_1")]

    restored = EventLog()
    restored.extend(Event.model_validate_json(raw) for raw in serialized)

    assert restored.events("run_1") == source.events("run_1")
    assert restored.verify().ok


def test_reload_rejects_a_forged_event() -> None:
    source = EventLog()
    seed(source, "run_1", 2)
    events = list(source.events("run_1"))
    forged = events[1].model_copy(update={"payload": {"tool": "forged"}})

    restored = EventLog()
    with pytest.raises(AppendOnlyViolation, match="hash does not match"):
        restored.extend([events[0], forged])


def test_reload_rejects_out_of_order_events() -> None:
    source = EventLog()
    seed(source, "run_1", 3)
    events = list(source.events("run_1"))

    restored = EventLog()
    with pytest.raises(AppendOnlyViolation, match="expected sequence 1"):
        restored.extend([events[1]])


def test_reload_rejects_a_forked_chain() -> None:
    source = EventLog()
    seed(source, "run_1", 2)
    events = list(source.events("run_1"))
    forked = events[1].model_copy(update={"prev_hash": "0" * 64}).sealed()

    restored = EventLog()
    with pytest.raises(AppendOnlyViolation, match="broken hash chain"):
        restored.extend([events[0], forked])


def test_every_event_type_is_appendable() -> None:
    log = EventLog()
    for i, event_type in enumerate(EventType, start=1):
        event = log.append("run_all", event_type, {"n": i})
        assert event.type is event_type
    assert log.verify("run_all").ok
    assert log.last_sequence("run_all") == len(EventType)
