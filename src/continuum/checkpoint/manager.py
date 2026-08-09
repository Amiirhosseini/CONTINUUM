"""Creating and restoring semantic checkpoints.

A checkpoint bundles the projected state, the event cursor it was projected
from, and (later) the environment it was verified against. Sealing it with an
integrity hash makes it the unit recovery trusts.

Ordering matters here. The manager writes the version, then the checkpoint,
then records ``STATE_CHECKPOINTED``. If the process dies partway:

* died before the version was written — nothing is lost; the state is still
  derivable from the events.
* died after the version but before the checkpoint — a version exists with no
  checkpoint. Harmless: the next checkpoint reuses it.
* died after the checkpoint but before the event — the checkpoint exists and is
  valid; the log simply lacks the annotation. ``restore`` reads checkpoints, not
  the annotation, so recovery is unaffected.

No ordering leaves a checkpoint that claims to cover events it does not, which
is the failure that would actually cause data loss.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from continuum.checkpoint.policy import (
    CheckpointDecision,
    CheckpointPolicy,
    CheckpointTrigger,
    PolicyContext,
    default_policy,
)
from continuum.events import EventType
from continuum.models import (
    EnvironmentSnapshot,
    SemanticState,
    StateCheckpoint,
    utcnow,
)
from continuum.state.semantic import project
from continuum.storage.base import Storage

__all__ = ["CheckpointManager", "RestoredRun", "CheckpointError"]


class CheckpointError(RuntimeError):
    """A checkpoint could not be created or restored."""


@dataclass(frozen=True, slots=True)
class RestoredRun:
    """What recovery gets back: verified state plus how stale it is.

    ``pending_events`` is the gap between the checkpoint and the end of the
    log — work that happened after the last checkpoint. It is replayed onto the
    checkpoint rather than ignored, so a crash between checkpoints does not
    discard the work in between.
    """

    run_id: str
    state: SemanticState
    checkpoint: StateCheckpoint | None
    pending_events: int
    replayed: bool

    @property
    def from_checkpoint(self) -> bool:
        return self.checkpoint is not None


class CheckpointManager:
    """Decides when to checkpoint, writes them, and restores from them."""

    def __init__(
        self,
        storage: Storage,
        *,
        policy: CheckpointPolicy | None = None,
    ) -> None:
        self.storage = storage
        self.policy = policy or default_policy()
        self._last_checkpoint_at: dict[str, datetime] = {}
        self._last_state: dict[str, SemanticState] = {}
        self._annotation_sequence: dict[str, int] = {}

    # -- deciding --------------------------------------------------------- #

    def evaluate(
        self,
        run_id: str,
        *,
        state: SemanticState | None = None,
        explicit: bool = False,
        context_tokens: int | None = None,
        now: datetime | None = None,
    ) -> CheckpointDecision:
        """Ask the policy whether a checkpoint is warranted right now."""
        current = state if state is not None else self.project_current(run_id)
        previous = self._last_state.get(run_id)
        last_at = self._last_checkpoint_at.get(run_id)

        if last_at is None:
            existing = self.storage.latest_checkpoint(run_id)
            if existing is not None:
                last_at = existing.created_at
                self._last_checkpoint_at[run_id] = last_at

        cursor = previous.source_sequence if previous else 0
        new_events = self.storage.read_events(run_id, after_sequence=cursor)

        return self.policy.should_checkpoint(
            PolicyContext(
                state=current,
                previous_state=previous,
                new_events=new_events,
                last_checkpoint_at=last_at,
                now=now or utcnow(),
                explicit=explicit,
                context_tokens=context_tokens,
            )
        )

    def maybe_checkpoint(
        self,
        run_id: str,
        *,
        state: SemanticState | None = None,
        explicit: bool = False,
        context_tokens: int | None = None,
        environment: EnvironmentSnapshot | None = None,
        now: datetime | None = None,
    ) -> StateCheckpoint | None:
        """Checkpoint if the policy agrees. Returns ``None`` when it declines."""
        current = state if state is not None else self.project_current(run_id)
        decision = self.evaluate(
            run_id,
            state=current,
            explicit=explicit,
            context_tokens=context_tokens,
            now=now,
        )
        if not decision.should:
            return None
        return self.checkpoint(
            run_id,
            state=current,
            trigger=decision.trigger,
            reason=decision.reason,
            environment=environment,
        )

    # -- writing ---------------------------------------------------------- #

    def project_current(self, run_id: str) -> SemanticState:
        """Fold the run's full event history into state."""
        return project(run_id, self.storage.read_events(run_id))

    def checkpoint(
        self,
        run_id: str,
        *,
        state: SemanticState | None = None,
        trigger: str = CheckpointTrigger.MANUAL,
        reason: str = "",
        environment: EnvironmentSnapshot | None = None,
    ) -> StateCheckpoint:
        """Create, seal and persist a checkpoint unconditionally."""
        current = state if state is not None else self.project_current(run_id)
        if current.run_id != run_id:
            raise CheckpointError(f"state belongs to run {current.run_id!r}, not {run_id!r}")

        version = self.storage.put_version(current, reason=reason or trigger)

        checkpoint = StateCheckpoint(
            run_id=run_id,
            version=version,
            trigger=trigger,
            state=current.model_copy(update={"version": version}),
            environment=environment,
        ).sealed()
        stored = self.storage.put_checkpoint(checkpoint)

        annotation = self.storage.append_event(
            run_id,
            EventType.STATE_CHECKPOINTED,
            {
                "checkpoint_id": stored.checkpoint_id,
                "version": version,
                "trigger": trigger,
                "reason": reason,
                "source_sequence": current.source_sequence,
                "integrity_hash": stored.integrity_hash,
            },
        )

        self._last_checkpoint_at[run_id] = stored.created_at
        self._last_state[run_id] = stored.state
        self._annotation_sequence[run_id] = annotation.sequence
        return stored

    def _cursor_for(self, checkpoint: StateCheckpoint) -> int:
        """How far into the log a checkpoint really covers.

        The ``STATE_CHECKPOINTED`` annotation is written *after* the state was
        projected, so it always sits one past the projected cursor. Counting it
        as unreplayed work would make every freshly-checkpointed run look stale
        and would replay a no-op event on every restore. The annotation carries
        no state, so the cursor advances past it.
        """
        cursor = checkpoint.state.source_sequence
        for event in self.storage.read_events(
            checkpoint.run_id, after_sequence=cursor, upto=cursor + 1
        ):
            if (
                event.type is EventType.STATE_CHECKPOINTED
                and event.payload.get("checkpoint_id") == checkpoint.checkpoint_id
            ):
                return event.sequence
        return cursor

    # -- restoring -------------------------------------------------------- #

    def restore(self, run_id: str, *, replay: bool = True) -> RestoredRun:
        """Load the newest checkpoint and catch it up to the log.

        With ``replay=False`` the checkpoint is returned as-is, which is what a
        validator wants when it must judge the checkpoint on its own terms
        before trusting anything newer.
        """
        checkpoint = self.storage.latest_checkpoint(run_id)

        if checkpoint is None:
            events = self.storage.read_events(run_id)
            if not events:
                raise CheckpointError(f"run {run_id!r} has no checkpoint and no events")
            return RestoredRun(
                run_id=run_id,
                state=project(run_id, events),
                checkpoint=None,
                pending_events=len(events),
                replayed=True,
            )

        if not checkpoint.verify():  # pragma: no cover - storage refuses these on read
            raise CheckpointError(
                f"checkpoint {checkpoint.checkpoint_id!r} failed its integrity check"
            )

        cursor = self._cursor_for(checkpoint)
        pending = self.storage.read_events(run_id, after_sequence=cursor)

        if not replay or not pending:
            return RestoredRun(
                run_id=run_id,
                state=checkpoint.state,
                checkpoint=checkpoint,
                pending_events=len(pending),
                replayed=False,
            )

        from continuum.state.semantic import project_incremental

        state, _ = project_incremental(run_id, pending, base=checkpoint.state)
        return RestoredRun(
            run_id=run_id,
            state=state,
            checkpoint=checkpoint,
            pending_events=len(pending),
            replayed=True,
        )

    def history(self, run_id: str) -> Sequence[StateCheckpoint]:
        return self.storage.list_checkpoints(run_id)
