"""MCP server exposing CONTINUUM to Claude Code and other MCP clients.

A thin layer over ``GenericAgentAdapter``. Every tool delegates to the adapter,
which already wraps ``CheckpointManager``, ``RecoveryEngine`` and
``ActionLedger``. Nothing here re-implements recovery logic; if a behaviour
looks wrong, the fix belongs in the layer below.

Tool results mirror the CLI's ``--json`` output so an agent, a script and a
human reading terminal output all see the same shape.

The action-interception split
-----------------------------

``continuum_intercept_action`` cannot execute the side effect itself: a Python
callable does not cross the MCP boundary. So the protocol is two calls —

1. ``continuum_intercept_action`` claims the action and answers *may I?*
2. the caller performs the effect, then reports back with
   ``continuum_complete_action`` (or ``continuum_fail_action``)

That split matters. Between the two calls the ledger holds a ``STARTED``
record, so a crash in the gap is indistinguishable from a completed effect —
which is exactly the state the ledger is designed to surface rather than
paper over. A caller that never reports back leaves the action uncertain, and
recovery will refuse to resume until it is reconciled. That is the intended
behaviour, not a leak.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from continuum.actions.ledger import ActionLedger
from continuum.adapters.generic import GenericAgentAdapter
from continuum.environment import StaticProvider, capture
from continuum.events import EventType
from continuum.models import (
    ActionStatus,
    EnvironmentSnapshot,
    EnvResource,
    Origin,
    Run,
    UnknownSideEffect,
)
from continuum.recovery.contract import render_contract
from continuum.state.semantic import project
from continuum.storage import RunNotFound, SQLiteStorage, Storage

__all__ = ["build_server", "ContinuumMCP", "MalformedRunLog", "DEFAULT_DB", "main"]

DEFAULT_DB = "continuum.db"
_DB_ENV_VAR = "CONTINUUM_DB"
_MUTATING_CLIENTS_ENV_VAR = "CONTINUUM_MCP_MUTATING_CLIENTS"

#: Everything written through this server is asserted by a remote agent about
#: its own work. Nothing here is independently verified, so it is recorded as
#: self-certified and cannot by itself establish that a run is safe to resume.
AGENT_SOURCE = Origin.EXTERNAL_AGENT


class MalformedRunLog(RuntimeError):
    """A run's event log does not begin with ``RUN_STARTED``.

    Raised rather than repaired: backfilling a start event behind existing
    history would misorder the run and yield a projection that is wrong in a
    way nothing downstream can detect.
    """


def resolve_database(explicit: str | None = None) -> str:
    """Where to store runs: explicit argument, then env var, then cwd default."""
    return explicit or os.environ.get(_DB_ENV_VAR) or DEFAULT_DB


def _environment(run_id: str, env: Mapping[str, str] | None) -> EnvironmentSnapshot | None:
    """Build a snapshot from a ``{name: version}`` mapping.

    Returns ``None`` when nothing was supplied. The validator treats that as
    *unverified*, not *unchanged* — omitting the environment must never look
    like having checked it and found nothing wrong.
    """
    if not env:
        return None
    resources = {
        name: EnvResource(name=name, version=str(version)) for name, version in env.items()
    }
    return capture(run_id, StaticProvider(resources))


class ContinuumMCP:
    """Holds the storage handle and adapter shared by every tool."""

    def __init__(self, database: str | None = None, *, storage: Storage | None = None) -> None:
        self.database = resolve_database(database)
        self.storage: Storage = storage or SQLiteStorage(self.database)
        self.adapter = GenericAgentAdapter(self.storage)
        self.allowed_mutating_clients = frozenset(
            client
            for client in (
                name.strip() for name in os.environ.get(_MUTATING_CLIENTS_ENV_VAR, "").split(",")
            )
            if client
        )

    def close(self) -> None:
        self.storage.close()

    # -- helpers shared by the tools -------------------------------------- #

    def ensure_run(self, run_id: str, goal: str | None = None) -> Run:
        """Fetch a run, creating it on first use if a goal was supplied.

        The run row and the ``RUN_STARTED`` event are separate facts: a row can
        exist without the event when the run was created directly through the
        storage API. Projection needs the event — without it, folding the log
        fails with "the log never recorded RUN_STARTED" — so it is backfilled
        when the log is empty.

        ``RUN_STARTED`` must be the *first* event, and this checks for exactly
        that rather than for any event at all. Checking "is the log non-empty"
        would be correct only by accident: it happens to hold today because
        every MCP tool calls this first, so nothing else can get in ahead. The
        moment another writer appends first, that assumption breaks silently.

        A non-empty log whose first event is not ``RUN_STARTED`` raises instead
        of backfilling. Appending it at that point would place the run's start
        *after* events that supposedly preceded it, and any state projected
        from that log would be quietly wrong — a worse outcome than an error
        naming the problem.
        """
        try:
            run = self.storage.get_run(run_id)
        except RunNotFound:
            if goal is None:
                raise
            run = self.storage.create_run(Run(run_id=run_id, goal=goal))

        first = self.storage.read_events(run_id, upto=1)
        if not first:
            self.storage.append_event(
                run_id,
                EventType.RUN_STARTED,
                {"goal": goal or run.goal},
                source=AGENT_SOURCE,
            )
        elif first[0].type is not EventType.RUN_STARTED:
            raise MalformedRunLog(
                f"run {run_id!r} does not begin with RUN_STARTED "
                f"(first event is {first[0].type.value}). CONTINUUM cannot backfill it "
                f"after the fact without misordering the run's history; recreate the "
                f"run, or record RUN_STARTED before any other event."
            )
        return run

    def ledger(self, run_id: str) -> ActionLedger:
        return ActionLedger(self.storage, run_id)

    def require_mutating_tool_authorization(
        self,
        tool_name: str,
        mcp_context: Context[Any, Any] | None,
    ) -> None:
        """Allow mutating tools only for configured MCP clients."""
        if mcp_context is None:
            return
        try:
            params = mcp_context.session.client_params
        except ValueError:
            params = None
        client_name = params.client_info.name if params and params.client_info else None
        if client_name in self.allowed_mutating_clients:
            return

        allowed = ", ".join(sorted(self.allowed_mutating_clients)) or "(none configured)"
        caller = client_name or "<unknown>"
        raise ToolError(
            f"{tool_name} is mutating and not authorized for MCP client {caller!r}. "
            f"Allowed mutating clients: {allowed}. Configure {_MUTATING_CLIENTS_ENV_VAR}."
        )


def build_server(
    database: str | None = None,
    *,
    storage: Storage | None = None,
) -> tuple[MCPServer, ContinuumMCP]:
    """Construct the MCP server and its backing context.

    Returns both so tests can drive tools directly and inspect the store.
    """
    ctx = ContinuumMCP(database, storage=storage)
    server = MCPServer(
        name="continuum",
        title="CONTINUUM",
        instructions=(
            "Durable recovery for long-running work. Record progress as you go, "
            "checkpoint at meaningful milestones, and before resuming after any "
            "interruption call continuum_resume to find out whether it is safe to "
            "continue. Route every external side effect through "
            "continuum_intercept_action so it is never performed twice."
        ),
    )

    read_only = ToolAnnotations(read_only_hint=True)
    mutating = ToolAnnotations(read_only_hint=False)

    # -- progress --------------------------------------------------------- #

    @server.tool(
        name="continuum_record_progress",
        description=(
            "Record how far through a task you are. Call this as you complete units "
            "of work so progress survives a crash. Creates the run on first call if "
            "'goal' is given. Cheap — call it often."
        ),
        annotations=mutating,
    )
    def continuum_record_progress(
        run_id: str,
        completed: int,
        total: int | None = None,
        goal: str | None = None,
        failed: int = 0,
        mcp_context: Context[Any, Any] | None = None,
    ) -> str:
        """Record progress for a run."""
        ctx.require_mutating_tool_authorization("continuum_record_progress", mcp_context)
        ctx.ensure_run(run_id, goal)
        payload: dict[str, Any] = {"completed": completed, "failed": failed}
        if total is not None:
            payload["total"] = total
            payload["pending"] = max(total - completed - failed, 0)
        ctx.storage.append_event(run_id, EventType.TASK_UPDATED, payload, source=AGENT_SOURCE)

        state = project(run_id, ctx.storage.read_events(run_id))
        return _json(
            {
                "run_id": run_id,
                "completed": state.progress.completed,
                "pending": state.progress.pending,
                "failed": state.progress.failed,
                "total": state.progress.total,
                "source_sequence": state.source_sequence,
            }
        )

    # -- checkpointing ---------------------------------------------------- #

    @server.tool(
        name="continuum_checkpoint",
        description=(
            "Save a durable checkpoint of the current task state. Worth doing at "
            "milestones, before risky or irreversible steps, and before a long gap. "
            "Recovery replays from the newest checkpoint, so checkpointing bounds "
            "how much work a crash can cost."
        ),
        annotations=mutating,
    )
    def continuum_checkpoint(
        run_id: str,
        reason: str = "",
        env: dict[str, str] | None = None,
        mcp_context: Context[Any, Any] | None = None,
    ) -> str:
        """Create a semantic checkpoint."""
        ctx.require_mutating_tool_authorization("continuum_checkpoint", mcp_context)
        ctx.ensure_run(run_id)
        state = project(run_id, ctx.storage.read_events(run_id))
        checkpoint = ctx.adapter.capture_state(
            run_id,
            state,
            environment=_environment(run_id, env),
            reason=reason,
        )
        return _json(
            {
                "checkpoint_id": checkpoint.checkpoint_id,
                "run_id": run_id,
                "version": checkpoint.version,
                "trigger": checkpoint.trigger,
                "integrity_hash": checkpoint.integrity_hash,
                "completed": checkpoint.state.progress.completed,
                "source_sequence": checkpoint.state.source_sequence,
            }
        )

    # -- validation ------------------------------------------------------- #

    @server.tool(
        name="continuum_validate",
        description=(
            "Check whether saved state is still trustworthy, without changing "
            "anything. Pass 'env' as {resource: version} to declare what the world "
            "looks like now — a dependency that moved since the checkpoint "
            "invalidates the findings built on it. Read-only: safe to call anytime."
        ),
        annotations=read_only,
    )
    def continuum_validate(
        run_id: str,
        env: dict[str, str] | None = None,
        expected_model: str | None = None,
    ) -> str:
        """Validate a run's state against the current environment."""
        decision = ctx.adapter.resume(
            run_id,
            current_environment=_environment(run_id, env),
            expected_model=expected_model,
        )
        report = decision.validation.report
        return _json(
            {
                "run_id": run_id,
                "safe": decision.safe,
                "mode": decision.mode.value,
                "checkpoint_version": report.checkpoint_version,
                "reason": report.reason,
                "components": [
                    {
                        "component": e.component.value,
                        "component_id": e.component_id,
                        "status": e.status.value,
                        "detail": e.detail,
                    }
                    for e in report.statuses
                ],
                "environment_changes": [d.render() for d in decision.environment_diff.breaking],
            }
        )

    # -- recovery --------------------------------------------------------- #

    @server.tool(
        name="continuum_resume",
        description=(
            "Ask whether it is safe to continue a run after any interruption, and "
            "what to do first. Call this BEFORE resuming work. Returns a mode: "
            "'resume' means proceed; anything else means stop and perform "
            "'next_allowed_action' first. Read-only."
        ),
        annotations=read_only,
    )
    def continuum_resume(
        run_id: str,
        env: dict[str, str] | None = None,
        expected_model: str | None = None,
    ) -> str:
        """Compute a recovery decision and contract."""
        decision = ctx.adapter.resume(
            run_id,
            current_environment=_environment(run_id, env),
            expected_model=expected_model,
        )
        return _json(
            {
                "run_id": run_id,
                "mode": decision.mode.value,
                "safe": decision.safe,
                "next_allowed_action": decision.next_allowed_action,
                "rationale": list(decision.rationale),
                "repairs": [
                    {
                        "action": step.action_name,
                        "kind": step.kind.value,
                        "target": step.target,
                        "reason": step.reason,
                        "requires_human": step.requires_human,
                    }
                    for step in decision.plan.steps
                ],
                "uncertain_actions": [
                    {
                        "action_id": a.action_id,
                        "action_type": a.action_type,
                        "status": a.status.value,
                    }
                    for a in decision.uncertain_actions
                ],
                "progress": {
                    "completed": decision.state.progress.completed,
                    "pending": decision.state.progress.pending,
                    "failed": decision.state.progress.failed,
                    "total": decision.state.progress.total,
                },
                "contract": decision.contract.model_dump(mode="json"),
                "contract_text": render_contract(decision.contract),
                "report": decision.render(),
            }
        )

    # -- side effects ----------------------------------------------------- #

    @server.tool(
        name="continuum_intercept_action",
        description=(
            "Ask permission before performing an external side effect (creating an "
            "issue, sending a message, charging a card). Returns proceed=true if you "
            "should do it, or proceed=false with the previous result if it was "
            "already done — do NOT repeat it in that case. If a previous attempt was "
            "interrupted, returns proceed=false with status='unknown': the effect may "
            "or may not have happened, so stop and ask a human. After performing the "
            "action, always call continuum_complete_action."
        ),
        annotations=mutating,
    )
    def continuum_intercept_action(
        run_id: str,
        action_type: str,
        arguments: dict[str, Any] | None = None,
        scoped_to_run: bool = True,
        mcp_context: Context[Any, Any] | None = None,
    ) -> str:
        """Claim an action in the ledger and report whether to proceed."""
        ctx.require_mutating_tool_authorization("continuum_intercept_action", mcp_context)
        ctx.ensure_run(run_id)
        ledger = ctx.ledger(run_id)
        try:
            outcome = ledger.claim(action_type, arguments=arguments, scoped_to_run=scoped_to_run)
        except UnknownSideEffect as exc:
            return _json(
                {
                    "run_id": run_id,
                    "action_type": action_type,
                    "proceed": False,
                    "status": ActionStatus.UNKNOWN.value,
                    "reason": str(exc),
                    "guidance": (
                        "A previous attempt was interrupted and its outcome is "
                        "unknown. Do not retry. Verify with the external system "
                        "whether it happened, then report via "
                        "continuum_reconcile_action."
                    ),
                }
            )

        if outcome.fresh:
            return _json(
                {
                    "run_id": run_id,
                    "action_type": action_type,
                    "proceed": True,
                    "action_key": str(outcome.key),
                    "status": outcome.action.status.value,
                    "guidance": (
                        "Perform the action now, then call continuum_complete_action "
                        "with this action_key."
                    ),
                }
            )

        return _json(
            {
                "run_id": run_id,
                "action_type": action_type,
                "proceed": False,
                "action_key": str(outcome.key),
                "status": outcome.action.status.value,
                "external_id": outcome.external_id,
                "previous_result": dict(outcome.result) if outcome.result else None,
                "guidance": "Already performed. Reuse the previous result; do not repeat it.",
            }
        )

    @server.tool(
        name="continuum_complete_action",
        description=(
            "Report that an intercepted action succeeded. Call this immediately "
            "after performing the side effect, using the action_key returned by "
            "continuum_intercept_action. Skipping it leaves the action uncertain "
            "and blocks recovery."
        ),
        annotations=mutating,
    )
    def continuum_complete_action(
        run_id: str,
        action_key: str,
        external_id: str | None = None,
        result: dict[str, Any] | None = None,
        mcp_context: Context[Any, Any] | None = None,
    ) -> str:
        """Mark a claimed action as completed."""
        ctx.require_mutating_tool_authorization("continuum_complete_action", mcp_context)
        action = ctx.ledger(run_id).complete(action_key, external_id=external_id, result=result)
        return _json(
            {
                "run_id": run_id,
                "action_id": action.action_id,
                "action_type": action.action_type,
                "status": action.status.value,
                "external_id": action.external_id,
            }
        )

    @server.tool(
        name="continuum_fail_action",
        description=(
            "Report that an intercepted action failed. Set certain=true only if you "
            "know nothing happened (e.g. the request was rejected before it was "
            "sent). For timeouts or dropped connections leave certain=false — the "
            "effect may still have landed, and treating it as failed could cause a "
            "duplicate."
        ),
        annotations=mutating,
    )
    def continuum_fail_action(
        run_id: str,
        action_key: str,
        error: str,
        certain: bool = False,
        mcp_context: Context[Any, Any] | None = None,
    ) -> str:
        """Mark a claimed action as failed or uncertain."""
        ctx.require_mutating_tool_authorization("continuum_fail_action", mcp_context)
        action = ctx.ledger(run_id).fail(action_key, error, certain=certain)
        return _json(
            {
                "run_id": run_id,
                "action_id": action.action_id,
                "status": action.status.value,
                "side_effect_uncertain": action.side_effect_uncertain,
            }
        )

    @server.tool(
        name="continuum_reconcile_action",
        description=(
            "Settle an action whose outcome was unknown, after checking the external "
            "system. occurred=true records it as done (never repeated); "
            "occurred=false frees it to be retried. Only call this with real "
            "evidence — guessing here causes either a duplicate or lost work."
        ),
        annotations=mutating,
    )
    def continuum_reconcile_action(
        run_id: str,
        action_key: str,
        occurred: bool,
        external_id: str | None = None,
        note: str = "",
        mcp_context: Context[Any, Any] | None = None,
    ) -> str:
        """Resolve an uncertain action using external evidence."""
        ctx.require_mutating_tool_authorization("continuum_reconcile_action", mcp_context)
        action = ctx.ledger(run_id).reconcile(
            action_key, occurred=occurred, external_id=external_id, note=note
        )
        return _json(
            {
                "run_id": run_id,
                "action_id": action.action_id,
                "status": action.status.value,
                "external_id": action.external_id,
                "side_effect_uncertain": action.side_effect_uncertain,
            }
        )

    @server.tool(
        name="continuum_list_actions",
        description=(
            "List external side effects recorded for a run, flagging any with "
            "unresolved outcomes. Read-only."
        ),
        annotations=read_only,
    )
    def continuum_list_actions(run_id: str) -> str:
        """List ledger entries for a run."""
        ctx.ensure_run(run_id)
        ledger = ctx.ledger(run_id)
        actions = ledger.all()
        return _json(
            {
                "run_id": run_id,
                "actions": [
                    {
                        "action_id": a.action_id,
                        "action_type": a.action_type,
                        "status": a.status.value,
                        "external_id": a.external_id,
                        "side_effect_uncertain": a.side_effect_uncertain,
                    }
                    for a in actions
                ],
                "unresolved": len(ledger.pending()),
            }
        )

    return server, ctx


def _json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``continuum-mcp``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="continuum-mcp",
        description="MCP server exposing CONTINUUM's durable recovery tools.",
    )
    parser.add_argument(
        "--db",
        default=None,
        help=f"storage path (default: ${_DB_ENV_VAR} or ./{DEFAULT_DB})",
    )
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=("stdio", "sse", "streamable-http"),
        help="MCP transport (default: stdio)",
    )
    args = parser.parse_args(argv)

    server, ctx = build_server(args.db)
    try:
        server.run(transport=args.transport)
    finally:
        ctx.close()
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess
    raise SystemExit(main())
