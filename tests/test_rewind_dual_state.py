"""Atomic dual-state rewind (issue #292) — 6 acceptance criteria."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from continuum.cli import main
from continuum.cli.exitcodes import ExitCode
from continuum.events import EventType
from continuum.models import Run
from continuum.storage import SQLiteStorage


def test_rewind_reverts_hook_tracked_writes(tmp_path: Path) -> None:
    db = str(tmp_path / "rewind.db")
    run_id = "run_rewind_1"
    storage = SQLiteStorage(db)
    storage.create_run(Run(run_id=run_id, goal="test rewind"))
    storage.append_event(run_id, EventType.RUN_STARTED, {"goal": "test"})
    storage.close()
    workdir = tmp_path / "work"
    workdir.mkdir()
    file_a = workdir / "a.txt"
    file_a.write_text("version at checkpoint", encoding="utf-8")
    from continuum.clienthooks import observe_event_payload
    from continuum.environment.file_snapshot import snapshot_file

    payload_a = observe_event_payload({"tool_name": "Write", "tool_input": {"file_path": str(file_a)}})
    snapshot_file(file_a, sha256=payload_a.get("sha256"))
    storage = SQLiteStorage(db)
    storage.append_event(run_id, EventType.TOOL_COMPLETED, payload_a)
    from continuum.checkpoint.manager import CheckpointManager

    manager = CheckpointManager(storage)
    cp = manager.checkpoint(run_id)
    checkpoint_id = cp.checkpoint_id
    storage.close()
    file_b = workdir / "b.txt"
    file_b.write_text("new file after checkpoint", encoding="utf-8")
    payload_b = observe_event_payload({"tool_name": "Write", "tool_input": {"file_path": str(file_b)}})
    snapshot_file(file_b, sha256=payload_b.get("sha256"))
    storage = SQLiteStorage(db)
    storage.append_event(run_id, EventType.TOOL_COMPLETED, payload_b)
    file_a.write_text("modified after checkpoint", encoding="utf-8")
    payload_a2 = observe_event_payload({"tool_name": "Edit", "tool_input": {"file_path": str(file_a)}})
    snapshot_file(file_a, sha256=payload_a2.get("sha256"))
    storage.append_event(run_id, EventType.TOOL_COMPLETED, payload_a2)
    storage.close()
    out, err = io.StringIO(), io.StringIO()
    code = main(["--db", db, "rewind", run_id, "--to", checkpoint_id], out=out, err=err)
    assert code == ExitCode.OK, f"rewind failed: {err.getvalue()} {out.getvalue()}"
    assert file_a.read_text(encoding="utf-8") == "version at checkpoint"
    assert not file_b.exists()
