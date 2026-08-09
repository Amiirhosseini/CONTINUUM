"""Append-only event log.

The event log is the source of truth for a run. Semantic state, checkpoints and
the action ledger are all *projections* of this log, which means recovery can
always be re-derived and independently audited.

Integrity model
---------------
Events form a per-run hash chain::

    e1.prev_hash = None          e1.hash = H(content(e1))
    e2.prev_hash = e1.hash       e2.hash = H(content(e2))
    ...

``EventLog.verify()`` recomputes every digest and re-walks the chain, so a
persisted log that was edited out-of-band is detectable. This is tamper
*evidence*, not tamper *proofing*: an attacker who can rewrite the whole log can
recompute the chain. Signing is out of scope for Phase 1 and documented as such.

Ordering guarantees are per run, not global: sequence numbers start at 1 and
increase by exactly 1 within a ``run_id``. No cross-run ordering is implied.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from continuum.models import utcnow
from continuum.security.hashing import make_id, stable_hash

__all__ = [
    "EventType",
    "Event",
    "EventLog",
    "IntegrityViolation",
    "IntegrityReport",
    "AppendOnlyViolation",
]


class EventType(StrEnum):
    """The recorded vocabulary of a run.

    Types that mutate semantic state are folded by ``continuum.state.project``;
    the rest are recorded facts (audit trail, ledger, recovery history) that
    leave the projection unchanged.
    """

    # lifecycle
    RUN_STARTED = "RUN_STARTED"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_ABORTED = "RUN_ABORTED"
    TASK_UPDATED = "TASK_UPDATED"

    # tools
    TOOL_CALLED = "TOOL_CALLED"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    TOOL_FAILED = "TOOL_FAILED"

    # semantic state
    DECISION_CREATED = "DECISION_CREATED"
    DECISION_INVALIDATED = "DECISION_INVALIDATED"
    EVIDENCE_ADDED = "EVIDENCE_ADDED"
    FINDING_ADDED = "FINDING_ADDED"
    FINDING_INVALIDATED = "FINDING_INVALIDATED"
    WORK_ADDED = "WORK_ADDED"
    WORK_COMPLETED = "WORK_COMPLETED"
    DEPENDENCY_DECLARED = "DEPENDENCY_DECLARED"

    # approvals
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVAL_GRANTED = "APPROVAL_GRANTED"
    APPROVAL_REVOKED = "APPROVAL_REVOKED"

    # model identity
    MODEL_CHANGED = "MODEL_CHANGED"
    MODEL_ASSUMPTION_RECORDED = "MODEL_ASSUMPTION_RECORDED"

    # checkpoints, environment, recovery
    STATE_CHECKPOINTED = "STATE_CHECKPOINTED"
    STATE_VALIDATED = "STATE_VALIDATED"
    ENVIRONMENT_CHANGED = "ENVIRONMENT_CHANGED"
    RECOVERY_STARTED = "RECOVERY_STARTED"
    RECOVERY_COMPLETED = "RECOVERY_COMPLETED"
    RECOVERY_BLOCKED = "RECOVERY_BLOCKED"

    # action ledger
    ACTION_RECORDED = "ACTION_RECORDED"
    ACTION_RECONCILED = "ACTION_RECONCILED"
    ACTION_COMPENSATED = "ACTION_COMPENSATED"


class AppendOnlyViolation(RuntimeError):
    """Raised when an operation would rewrite history."""


class Event(BaseModel):
    """An immutable, hash-chained fact about a run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(default_factory=lambda: make_id("event"))
    run_id: str
    sequence: int
    type: EventType
    timestamp: datetime = Field(default_factory=utcnow)
    payload: Mapping[str, Any] = Field(default_factory=dict)
    causer_event_id: str | None = None
    prev_hash: str | None = None
    hash: str | None = None

    def content(self) -> dict[str, Any]:
        """The hashed portion of the event (everything except ``hash``)."""
        return {
            "event_id": self.event_id,
            "run_id": self.run_id,
            "sequence": self.sequence,
            "type": self.type.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
            "causer_event_id": self.causer_event_id,
            "prev_hash": self.prev_hash,
        }

    def digest(self) -> str:
        """Recompute this event's content hash."""
        return stable_hash(self.content())

    def sealed(self) -> Event:
        """Return a copy with ``hash`` set to the recomputed digest."""
        return self.model_copy(update={"hash": self.digest()})


class IntegrityViolation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    run_id: str
    sequence: int | None = None
    event_id: str | None = None
    detail: str = ""


class IntegrityReport(BaseModel):
    """Result of re-auditing one or more chains.

    ``trusted_through`` is the actionable field: for each run it gives the
    highest sequence number whose prefix verified completely. A recovery engine
    can rebuild state from that prefix and treat everything after it as
    unverifiable rather than discarding the whole run.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    ok: bool
    checked: int
    violations: list[IntegrityViolation] = Field(default_factory=list)
    trusted_through: dict[str, int] = Field(default_factory=dict)
    truncated: bool = False


class EventLog:
    """In-memory append-only log, partitioned by ``run_id``.

    Phase 3 backs this with SQLite; the interface stays the same so callers
    never depend on the storage engine.
    """

    def __init__(self) -> None:
        self._by_run: dict[str, list[Event]] = {}

    # -- writing ---------------------------------------------------------- #

    def append(
        self,
        run_id: str,
        type: EventType,
        payload: Mapping[str, Any] | None = None,
        *,
        causer_event_id: str | None = None,
        timestamp: datetime | None = None,
        event_id: str | None = None,
    ) -> Event:
        """Append an event and return the sealed (hashed) record."""
        chain = self._by_run.setdefault(run_id, [])
        head = chain[-1] if chain else None
        event = Event(
            event_id=event_id or make_id("event"),
            run_id=run_id,
            sequence=len(chain) + 1,
            type=type,
            timestamp=timestamp or utcnow(),
            payload=dict(payload or {}),
            causer_event_id=causer_event_id,
            prev_hash=head.hash if head else None,
        ).sealed()
        chain.append(event)
        return event

    def extend(self, events: Iterable[Event]) -> None:
        """Load already-sealed events (e.g. from storage), verifying the chain.

        Rejects anything that would rewrite or fork existing history.
        """
        for event in events:
            chain = self._by_run.setdefault(event.run_id, [])
            expected_sequence = len(chain) + 1
            if event.sequence != expected_sequence:
                raise AppendOnlyViolation(
                    f"run {event.run_id}: expected sequence {expected_sequence}, got {event.sequence}"
                )
            expected_prev = chain[-1].hash if chain else None
            if event.prev_hash != expected_prev:
                raise AppendOnlyViolation(
                    f"run {event.run_id} seq {event.sequence}: broken hash chain"
                )
            if event.hash != event.digest():
                raise AppendOnlyViolation(
                    f"run {event.run_id} seq {event.sequence}: event hash does not match content"
                )
            chain.append(event)

    # -- reading ---------------------------------------------------------- #

    def runs(self) -> tuple[str, ...]:
        return tuple(self._by_run)

    def events(self, run_id: str, *, after_sequence: int = 0) -> tuple[Event, ...]:
        chain = self._by_run.get(run_id, ())
        return tuple(e for e in chain if e.sequence > after_sequence)

    def by_type(self, run_id: str, type: EventType) -> tuple[Event, ...]:
        return tuple(e for e in self._by_run.get(run_id, ()) if e.type is type)

    def head(self, run_id: str) -> Event | None:
        chain = self._by_run.get(run_id)
        return chain[-1] if chain else None

    def last_sequence(self, run_id: str) -> int:
        return len(self._by_run.get(run_id, ()))

    def __iter__(self) -> Iterator[Event]:
        for chain in self._by_run.values():
            yield from chain

    def __len__(self) -> int:
        return sum(len(chain) for chain in self._by_run.values())

    # -- integrity -------------------------------------------------------- #

    def verify(self, run_id: str | None = None, *, max_violations: int = 1000) -> IntegrityReport:
        """Recompute every digest and re-walk the chain(s).

        The walk propagates the *recomputed* digest rather than the stored one,
        so an edited event is reported twice: ``TAMPERED_CONTENT`` on the event
        itself and ``BROKEN_CHAIN`` on its successor, whose link no longer
        matches. The walk then re-syncs, because untampered events remain
        internally consistent — so the violation list localises damage instead
        of flooding.

        Trust is expressed separately by ``trusted_through``: only the prefix
        before the first violation is considered verified. Events after it are
        readable but unverified, and callers must not treat them as authority.
        """
        run_ids = [run_id] if run_id is not None else list(self._by_run)
        violations: list[IntegrityViolation] = []
        trusted_through: dict[str, int] = {}
        checked = 0
        truncated = False

        def record(kind: str, rid: str, event: Event, detail: str) -> None:
            nonlocal truncated
            if len(violations) >= max_violations:
                truncated = True
                return
            violations.append(
                IntegrityViolation(
                    kind=kind,
                    run_id=rid,
                    sequence=event.sequence,
                    event_id=event.event_id,
                    detail=detail,
                )
            )

        for rid in run_ids:
            prev_digest: str | None = None
            expected_sequence = 1
            last_good = 0
            intact = True

            for event in self._by_run.get(rid, ()):
                checked += 1
                digest = event.digest()
                healthy = True

                if event.sequence != expected_sequence:
                    healthy = False
                    record("SEQUENCE_GAP", rid, event, f"expected sequence {expected_sequence}")
                if event.hash != digest:
                    healthy = False
                    record(
                        "TAMPERED_CONTENT",
                        rid,
                        event,
                        "stored hash does not match recomputed digest",
                    )
                if event.prev_hash != prev_digest:
                    healthy = False
                    record(
                        "BROKEN_CHAIN",
                        rid,
                        event,
                        f"prev_hash {event.prev_hash!r} does not match predecessor digest {prev_digest!r}",
                    )

                if healthy and intact:
                    last_good = event.sequence
                else:
                    intact = False

                prev_digest = digest
                expected_sequence = event.sequence + 1

            trusted_through[rid] = last_good

        return IntegrityReport(
            ok=not violations,
            checked=checked,
            violations=violations,
            trusted_through=trusted_through,
            truncated=truncated,
        )
