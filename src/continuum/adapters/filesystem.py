"""Pure-filesystem sandbox adapter (no external services).

This is the default adapter for docs and CI examples. It manages a local
sandbox directory and records every shell step through the ActionLedger, so it
enjoys recovery parity with the shell adapter without needing docker, a browser,
or a cluster. It subclasses :class:`GenericAgentAdapter` and adds a thin
sandbox surface on top of the real recovery primitives.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from continuum.adapters import run_action
from continuum.adapters.actions import AdapterAction, AdapterResult
from continuum.adapters.generic import GenericAgentAdapter
from continuum.recovery.engine import RecoveryEngine
from continuum.storage.base import Storage


class FilesystemSandboxAdapter(GenericAgentAdapter):
    """A filesystem-backed sandbox that records commands as idempotent actions."""

    def __init__(
        self,
        storage: Storage,
        sandbox_dir: str,
        *,
        engine: RecoveryEngine | None = None,
    ) -> None:
        super().__init__(storage, engine=engine)
        self.sandbox_dir = Path(sandbox_dir)
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)

    def run_shell(
        self, run_id: str, command: str, *, dep_scope: str | None = None
    ) -> AdapterResult:
        """Run ``command`` inside the sandbox dir, recorded as an action."""

        def _run() -> str:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=str(self.sandbox_dir),
                capture_output=True,
                text=True,
                check=True,
            )
            return completed.stdout

        return run_action(
            self,
            run_id,
            AdapterAction(name="shell", params={"command": command}, dep_scope=dep_scope),
            _run,
        )
