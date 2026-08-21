"""Hooks that make checkpoints independent of LLM discipline (issue 86).

The model may batch work and skip explicit checkpoint calls. A hook called
after each assistant turn or file write ensures a checkpoint is taken when
the policy says it is warranted, without relying on the model to remember the
tool call. Issue 187 adds an async variant that does not block the agent turn.
"""

from __future__ import annotations

import concurrent.futures
from collections.abc import Callable
from pathlib import Path

from continuum.checkpoint import CheckpointManager
from continuum.events import EventType
from continuum.models import EnvironmentSnapshot, Origin


def make_auto_checkpoint_hook(
    manager: CheckpointManager,
    run_id: str,
    *,
    environment: EnvironmentSnapshot | None = None,
) -> Callable[[], bool]:
    """Return a callable that checkpoints when the policy says to.

    The hook is meant to be called from an agent framework hook point, for
    example after each assistant turn or after each file write. It delegates
    to ``CheckpointManager.maybe_checkpoint`` and returns True when a checkpoint
    was created, False otherwise. The hook never raises on policy no.
    """

    def hook() -> bool:
        result = manager.maybe_checkpoint(run_id, environment=environment)
        return result is not None

    return hook


def make_async_auto_checkpoint_hook(
    manager: CheckpointManager,
    run_id: str,
    *,
    environment: EnvironmentSnapshot | None = None,
) -> Callable[[], bool]:
    """Return a hook that checkpoints in the background without blocking.

    The hook evaluates the policy synchronously, which is cheap, and only
    submits the actual checkpoint write to a background thread when the policy
    says a checkpoint is warranted. It returns immediately, so an agent turn is
    never blocked on SQLite I/O. This is the path that makes the five part
    guide stay at one model turn with a single end of task checkpoint, as
    measured for issue 187.
    """

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def hook() -> bool:
        executor.submit(manager.maybe_checkpoint, run_id, environment=environment)
        return True

    return hook


def count_sections(file_path: str | Path) -> int:
    """Count markdown sections by ^##  headings, the file as ground truth."""
    try:
        text = Path(file_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return 0
    return sum(1 for line in text.splitlines() if line.startswith("## "))


def make_file_derived_progress_hook(
    manager: CheckpointManager,
    run_id: str,
    file_path: str | Path,
    total: int,
    *,
    environment: EnvironmentSnapshot | None = None,
) -> Callable[[], bool]:
    """Derive completed from the file and record it atomically with a checkpoint.

    After each file write, count ^##  headings in file_path and append a
    TASK_UPDATED with that count, then maybe checkpoint. The file is ground
    truth, the ledger just mirrors it, so the counter can never run ahead as
    it did in issue 188. Returns True when progress was recorded.
    """

    def hook() -> bool:
        completed = count_sections(file_path)
        manager.storage.append_event(
            run_id,
            EventType.TASK_UPDATED,
            {"completed": completed, "total": total},
            source=Origin.EXTERNAL_AGENT,
        )
        manager.maybe_checkpoint(run_id, environment=environment)
        return True

    return hook
