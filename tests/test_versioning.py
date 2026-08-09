from __future__ import annotations

import pytest

from continuum.events import EventLog, EventType
from continuum.models import Goal, Progress, SemanticState
from continuum.state.versioning import VersionChain, state_fingerprint


def make_state(**overrides: object) -> SemanticState:
    base: dict[str, object] = {
        "run_id": "run_1",
        "goal": Goal(description="Analyze 100 documents"),
    }
    base.update(overrides)
    return SemanticState(**base)  # type: ignore[arg-type]


def test_first_commit_is_version_zero() -> None:
    chain = VersionChain("run_1")
    entry = chain.commit(make_state(), reason="start")
    assert entry is not None
    assert entry.version == 0
    assert entry.prev_fingerprint is None
    assert len(chain) == 1


def test_versions_increment_and_link() -> None:
    chain = VersionChain("run_1")
    first = chain.commit(make_state())
    second = chain.commit(make_state(progress=Progress(completed=1)))
    assert first is not None and second is not None
    assert second.version == 1
    assert second.prev_fingerprint == first.fingerprint
    assert chain.verify()


def test_committing_an_unchanged_state_records_nothing() -> None:
    chain = VersionChain("run_1")
    chain.commit(make_state())
    assert chain.commit(make_state()) is None
    assert len(chain) == 1


def test_fingerprint_ignores_bookkeeping_but_not_meaning() -> None:
    a = make_state()
    b = a.next_version()
    assert state_fingerprint(a) == state_fingerprint(b)

    c = a.model_copy(update={"progress": Progress(completed=1)})
    assert state_fingerprint(a) != state_fingerprint(c)


def test_committed_state_carries_the_chain_version() -> None:
    chain = VersionChain("run_1")
    chain.commit(make_state(version=99))
    head = chain.head
    assert head is not None
    assert head.state.version == 0


def test_history_is_addressable_by_version() -> None:
    chain = VersionChain("run_1")
    chain.commit(make_state())
    chain.commit(make_state(progress=Progress(completed=5)))
    assert chain.at(1).state.progress.completed == 5
    with pytest.raises(KeyError):
        chain.at(7)


def test_a_chain_rejects_states_from_another_run() -> None:
    chain = VersionChain("run_1")
    with pytest.raises(ValueError, match="belongs to run"):
        chain.commit(make_state(run_id="run_2"))


def test_verify_detects_an_edited_history() -> None:
    chain = VersionChain("run_1")
    chain.commit(make_state())
    chain.commit(make_state(progress=Progress(completed=1)))
    assert chain.verify()

    tampered = chain._entries[1].model_copy(
        update={
            "state": chain._entries[1].state.model_copy(
                update={"progress": Progress(completed=999)}
            )
        }
    )
    chain._entries[1] = tampered
    assert not chain.verify()


def test_chain_iteration_is_a_snapshot() -> None:
    chain = VersionChain("run_1")
    chain.commit(make_state())
    view = chain.entries
    chain.commit(make_state(progress=Progress(completed=1)))
    assert len(view) == 1
    assert len(chain.entries) == 2


def test_a_chain_built_from_a_projected_run_tracks_real_progress() -> None:
    from continuum.state.semantic import project

    log = EventLog()
    log.append("run_1", EventType.RUN_STARTED, {"goal": "Analyze 3 documents", "total": 3})
    chain = VersionChain("run_1")
    chain.commit(project("run_1", log.events("run_1")), reason="start")

    for _ in range(3):
        log.append("run_1", EventType.WORK_COMPLETED, {})
        chain.commit(project("run_1", log.events("run_1")), reason="progress")

    assert [e.version for e in chain] == [0, 1, 2, 3]
    assert chain.current is not None
    assert chain.current.progress.completed == 3
    assert chain.verify()
