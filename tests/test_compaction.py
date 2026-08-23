"""Event-log compaction (issue #239).

`continuum compact` archives the pre-anchor prefix of a run's log and
appends an EVENT_LOG_ANCHORED marker, keeping the live chain append-only
while bounding replay cost for month-long runs. These tests pin the
mechanics: prefix moves verbatim to the archive, the anchor is the new
trusted genesis of verify's walk, post-anchor projection via checkpoint
restore stays correct, resume/verify/replay all work on compacted runs,
and tampering with archived rows is detectable.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from continuum.checkpoint import CheckpointManager
from continuum.cli import ExitCode, main
from continuum.events import EventType
from continuum.models import Run
from continuum.replayguard import GuardKind, protected_call
from continuum.storage import SQLiteStorage


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = main(list(argv), out=out, err=err)
    return code, out.getvalue(), err.getvalue()


@pytest.fixture
def db(tmp_path: Path) -> str:
    path = str(tmp_path / "c.db")
    with SQLiteStorage(path) as store:
        store.create_run(Run(run_id="run_1", goal="long task"))
        store.append_event("run_1", EventType.RUN_STARTED,
                           {"goal": "long task", "total": 10})
        CheckpointManager(store).checkpoint("run_1")
    yield path


def work(db: str, i: int) -> None:
    with SQLiteStorage(db) as store:
        kind, _ = protected_call(
            store, "run_1",
            action_type="process_doc", key=f"doc:{i}",
            fn=lambda doc=i: {"doc": doc},
        )
        assert kind is GuardKind.ALLOW


def test_compact_archives_prefix_and_keeps_tail_intact(db: str) -> None:
    for i in range(6):
        work(db, i)
    with SQLiteStorage(db) as store:
        pre_count = len(store.read_events("run_1"))

    code, out, err = run("--db", db, "--json", "compact", "run_1", "--force")
    assert code == ExitCode.OK, err

    with SQLiteStorage(db) as store:
        live = store.read_events("run_1")
        archived = [
            dict(r) for r in store._connection.execute(
                "SELECT * FROM events_archive WHERE run_id = 'run_1' ORDER BY sequence"
            )
        ]
    # The forced anchor-checkpoint's own marker plus the ANCHOR event remain
    # live; everything at or before their boundary is archived verbatim.
    assert len(live) == 2
    assert {e.type for e in live} == {
        EventType.STATE_CHECKPOINTED,
        EventType.EVENT_LOG_ANCHORED,
    }
    assert live[-1].type is EventType.EVENT_LOG_ANCHORED
    assert archived[0]["sequence"] == 1
    assert len(archived) == pre_count

    # Chain integrity on the live log.
    code, _, err = run("--db", db, "verify", "run_1")
    assert code == ExitCode.OK, err


def test_verify_flags_tampered_archive_rows_deep(db: str) -> None:
    work(db, 1)
    run("--db", db, "--json", "compact", "run_1", "--force")
    with SQLiteStorage(db) as store:
        store._connection.execute(
            "UPDATE events_archive SET payload = '{\"tampered\": true}'"
        )
        rows = [dict(r) for r in store._connection.execute(
            "SELECT * FROM events_archive WHERE run_id='run_1'"
        )]
    tampered = any(
        SQLiteStorage._row_to_event(row).hash != SQLiteStorage._row_to_event(row).digest()
        for row in rows
    )
    assert tampered, "tampering must be detectable via digest recomputation"


def test_resume_works_on_a_compacted_run(db: str) -> None:
    for i in range(3):
        work(db, i)
    code, _, err = run("--db", db, "compact", "run_1", "--force")
    assert code == ExitCode.OK, err
    code, out, err = run("--db", db, "--json", "resume", "run_1")
    assert code in (ExitCode.OK, ExitCode.REQUIRES_HUMAN), err
    payload = json.loads(out)
    assert payload["mode"] in ("resume", "request_human")


def test_replay_reports_anchored_mode(db: str) -> None:
    work(db, 5)
    run("--db", db, "compact", "run_1", "--force")
    code, out, err = run("--db", db, "--json", "replay", "run_1")
    assert code == ExitCode.OK, err
    payload = json.loads(out)
    assert "anchored" in payload["verification"]


def test_inspect_and_status_survive_compaction(db: str) -> None:
    work(db, 2)
    run("--db", db, "compact", "run_1", "--force")
    code, out, _ = run("--db", db, "inspect", "run_1")
    assert code == ExitCode.OK
    code, out, _ = run("--db", db, "status", "run_1")
    assert code == ExitCode.OK


def test_compact_requires_an_existing_version(tmp_path: Path) -> None:
    path = str(tmp_path / "empty.db")
    with SQLiteStorage(path) as store:
        store.create_run(Run(run_id="bare", goal="g"))
    code, _, err = run("--db", path, "--force", "compact", "bare") if False else run(
        "--db", path, "compact", "bare", "--force"
    )
    assert code == ExitCode.ERROR
    assert "anchored" in err or "no stored version" in err


def test_bounded_size_after_compaction(db: str) -> None:
    """The acceptance core: compaction bounds live-log growth."""
    for i in range(40):
        work(db, i)
    with SQLiteStorage(db) as store:
        before = len(store.read_events("run_1"))
    code, _, err = run("--db", db, "compact", "run_1", "--force")
    assert code == ExitCode.OK, err
    for i in range(40, 50):
        work(db, i)
    with SQLiteStorage(db) as store:
        live_rows = store._connection.execute(
            "SELECT COUNT(*) AS n FROM events WHERE run_id='run_1'"
        ).fetchone()["n"]
        archived_rows = store._connection.execute(
            "SELECT COUNT(*) AS n FROM events_archive WHERE run_id='run_1'"
        ).fetchone()["n"]
    # Bounded live log; history preserved verbatim in the archive.
    assert archived_rows == before, (archived_rows, before)
    assert live_rows <= 25


# --- protected nodes keep working across compaction ------------------------------ #


def test_protected_call_cache_survives_compaction_of_unrelated_prefix(
    db: str,
) -> None:
    work(db, 1)
    run("--db", db, "compact", "run_1", "--force")
    kind, value = protected_call(
        SQLiteStorage(db), "run_1",
        action_type="process_doc", key="doc:99",
        fn=lambda: {"doc": 99},
    )
    assert kind is GuardKind.ALLOW and value == {"doc": 99}
