from pathlib import Path

from continuum.adapters.generic import GenericAgentAdapter
from continuum.events import EventType
from continuum.models import Run
from continuum.state.semantic import project
from continuum.storage import SQLiteStorage


def test_adapter_auto_derives_progress_from_file(tmp_path: Path) -> None:
    file = tmp_path / "guide.md"
    file.write_text("## A\n\n## B\n\n", encoding="utf-8")
    storage = SQLiteStorage(":memory:")
    storage.create_run(Run(run_id="run_1", goal="g"))
    storage.append_event("run_1", EventType.RUN_STARTED, {"goal": "g", "total": 5})
    adapter = GenericAgentAdapter(storage, auto_file=str(file), auto_total=5)
    state = project("run_1", storage.read_events("run_1"))
    adapter.capture_state("run_1", state)
    restored = project("run_1", storage.read_events("run_1"))
    assert restored.progress.completed == 2


def test_recovery_carries_tail_evidence(tmp_path: Path) -> None:
    file = tmp_path / "guide.md"
    file.write_text("## A\ncontent a\n\n## B\ncontent b\n", encoding="utf-8")
    storage = SQLiteStorage(":memory:")
    storage.create_run(Run(run_id="run_1", goal="g"))
    storage.append_event("run_1", EventType.RUN_STARTED, {"goal": "g", "total": 5})
    from continuum.checkpoint import CheckpointManager
    from continuum.hooks import make_file_derived_progress_hook

    manager = CheckpointManager(storage)
    hook = make_file_derived_progress_hook(manager, "run_1", file, total=5)
    hook()
    from continuum.recovery import RecoveryEngine

    decision = RecoveryEngine(storage).assess("run_1")
    assert decision.tail_evidence is not None
    assert "content b" in decision.tail_evidence
