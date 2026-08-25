"""Immutable version chain for semantic state.

Every accepted mutation appends a version. Versions are content-addressed and
linked, exactly like the event log, so a state history can be audited the same
way and `continuum history` / `continuum inspect --version N` have something
truthful to read.

The chain deliberately refuses to store two consecutive identical states: a
version should mean "something changed", otherwise checkpoint policies that
fire on a timer would inflate history with noise.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from continuum.models import SemanticState, utcnow
from continuum.security.hashing import stable_hash

__all__ = ["VersionEntry", "VersionChain", "state_fingerprint"]


def state_fingerprint(state: SemanticState) -> str:
    """Content hash of the *meaning* of a state, ignoring bookkeeping fields.

    Two states with the same goal, progress, decisions, findings, evidence,
    pending work, approvals and dependencies are the same state even if they
    were projected at different times or carry different version numbers.

    The projection-degradation fields are excluded for the same reason: they
    describe how the log was read (where folding stopped), not what the state
    says. Including them would break fingerprint dedup across the upgrade for
    every stored version, and a degraded prefix-state genuinely is the same
    task state as its healthy counterpart.
    """
    payload = state.model_dump(
        mode="json",
        exclude={
            "version",
            "created_at",
            "updated_at",
            "source_sequence",
            "status",
            "unprojectable_at_sequence",
            "unprojectable_event_type",
            "unprojectable_reason",
        },
    )
    return stable_hash(payload)


class VersionEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int
    state: SemanticState
    fingerprint: str
    prev_fingerprint: str | None = None
    reason: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class VersionChain:
    """Ordered, append-only sequence of state versions for one run."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._entries: list[VersionEntry] = []

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[VersionEntry]:
        return iter(tuple(self._entries))

    @property
    def entries(self) -> tuple[VersionEntry, ...]:
        return tuple(self._entries)

    @property
    def head(self) -> VersionEntry | None:
        return self._entries[-1] if self._entries else None

    @property
    def current(self) -> SemanticState | None:
        head = self.head
        return head.state if head else None

    def commit(self, state: SemanticState, *, reason: str = "") -> VersionEntry | None:
        """Append ``state`` as the next version.

        Returns ``None`` when the state is semantically unchanged, so callers
        can distinguish "recorded a new version" from "nothing happened".
        """
        if state.run_id != self.run_id:
            raise ValueError(f"state belongs to run {state.run_id!r}, not {self.run_id!r}")

        fingerprint = state_fingerprint(state)
        head = self.head
        if head is not None and head.fingerprint == fingerprint:
            return None

        version = (head.version + 1) if head else 0
        entry = VersionEntry(
            version=version,
            state=state.model_copy(update={"version": version}),
            fingerprint=fingerprint,
            prev_fingerprint=head.fingerprint if head else None,
            reason=reason,
        )
        self._entries.append(entry)
        return entry

    def at(self, version: int) -> VersionEntry:
        for entry in self._entries:
            if entry.version == version:
                return entry
        raise KeyError(f"run {self.run_id!r} has no version {version}")

    def verify(self) -> bool:
        """Recompute fingerprints and re-walk the links."""
        prev: str | None = None
        for expected, entry in enumerate(self._entries):
            if entry.version != expected:
                return False
            if entry.fingerprint != state_fingerprint(entry.state):
                return False
            if entry.prev_fingerprint != prev:
                return False
            prev = entry.fingerprint
        return True
