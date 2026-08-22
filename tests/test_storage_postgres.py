"""Contract tests for the PostgreSQL storage backend (B2.3).

These run the same core behaviors as the SQLite suite against a real Postgres.
They skip cleanly when ``CONTINUUM_TEST_POSTGRES_DSN`` is unset or ``psycopg`` is
not installed, so the suite stays green locally and is exercised for real in CI
with a Postgres service container.
"""

from __future__ import annotations

import os

import pytest

from continuum.models import Run, SemanticState
from continuum.storage.base import ConcurrentWriteError, RunNotFound
from continuum.storage.postgres import PostgresStorage

DSN = os.environ.get("CONTINUUM_TEST_POSTGRES_DSN")


def _psycopg_available() -> bool:
    try:
        import psycopg  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        return False
    return True


pytestmark = pytest.mark.skipif(
    DSN is None or not _psycopg_available(),
    reason="set CONTINUUM_TEST_POSTGRES_DSN and install continuum[postgres] to run",
)


@pytest.fixture
def storage() -> PostgresStorage:
    store = PostgresStorage(DSN)
    yield store
    store.close()


def test_run_lifecycle(storage: PostgresStorage) -> None:
    run = storage.create_run(Run(run_id="run_pg", goal="postgres run"))
    assert storage.get_run("run_pg").goal == "postgres run"
    assert storage.update_run(run.touch()).run_id == "run_pg"
    assert storage.list_runs()[-1].run_id == "run_pg"
    assert storage.get_active_run() is not None


def test_create_run_started_writes_row_and_first_event_together(
    storage: PostgresStorage,
) -> None:
    """Same atomicity contract as the SQLite backend (PR #206 review)."""
    storage.create_run_started(Run(run_id="run_pg_s", goal="Ship it"))

    assert storage.get_run("run_pg_s").goal == "Ship it"
    events = storage.read_events("run_pg_s")
    assert [e.type.value if hasattr(e.type, "value") else e.type for e in events] == ["RUN_STARTED"]
    assert storage.verify_events("run_pg_s").ok


def test_create_run_started_refuses_a_duplicate(storage: PostgresStorage) -> None:
    from continuum.models import Origin

    storage.create_run_started(Run(run_id="run_pg_d", goal="first"), source=Origin.HUMAN)
    with pytest.raises(ConcurrentWriteError, match="already exists"):
        storage.create_run_started(Run(run_id="run_pg_d", goal="second"), source=Origin.HUMAN)


def test_run_not_found(storage: PostgresStorage) -> None:
    with pytest.raises(RunNotFound):
        storage.get_run("ghost")


def test_event_chain_and_verification(storage: PostgresStorage) -> None:
    storage.create_run(Run(run_id="run_ev", goal="events"))
    storage.append_event("run_ev", "task_updated", {"k": "v"})
    storage.append_event("run_ev", "progress", {"n": 1})
    events = storage.read_events("run_ev")
    assert len(events) == 2
    assert events[0].sequence == 1
    assert storage.last_sequence("run_ev") == 2
    report = storage.verify_events("run_ev")
    assert report.ok is True
    assert report.trusted_through["run_ev"] == 2


def test_concurrent_sequence_is_refused(storage: PostgresStorage) -> None:
    storage.create_run(Run(run_id="run_c", goal="c"))
    storage.append_event("run_c", "a")
    with pytest.raises(ConcurrentWriteError):
        storage.append_event("run_c", "b", expected_sequence=0)


def test_versions_and_checkpoints(storage: PostgresStorage) -> None:
    storage.create_run(Run(run_id="run_v", goal="v"))
    state = SemanticState(run_id="run_v", goal="v")
    v1 = storage.put_version(state)
    assert v1 == 0
    # Same content is idempotent: no new version.
    assert storage.put_version(state) == 0
    assert storage.latest_version("run_v") is not None
    assert storage.list_versions("run_v") == [0]
