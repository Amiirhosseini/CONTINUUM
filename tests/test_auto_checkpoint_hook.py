from continuum.checkpoint import CheckpointManager
from continuum.events import EventType
from continuum.hooks import make_async_auto_checkpoint_hook, make_auto_checkpoint_hook
from continuum.models import Run
from continuum.storage import SQLiteStorage


def test_auto_checkpoint_hook_respects_policy() -> None:
    storage = SQLiteStorage(":memory:")
    storage.create_run(Run(run_id="run_1", goal="g"))
    storage.append_event("run_1", EventType.RUN_STARTED, {"goal": "g", "total": 1})
    manager = CheckpointManager(storage)
    hook = make_auto_checkpoint_hook(manager, "run_1")

    first = hook()
    assert first is True
    second = hook()
    assert second is False


def test_async_hook_does_not_block_and_still_checkpoints() -> None:
    storage = SQLiteStorage(":memory:")
    storage.create_run(Run(run_id="run_1", goal="g"))
    storage.append_event("run_1", EventType.RUN_STARTED, {"goal": "g", "total": 1})
    manager = CheckpointManager(storage)
    hook = make_async_auto_checkpoint_hook(manager, "run_1")

    import time

    start = time.perf_counter()
    result = hook()
    elapsed = time.perf_counter() - start

    assert result is True
    assert elapsed < 0.1

    time.sleep(0.2)
    assert storage.latest_checkpoint("run_1") is not None
