"""Fork semantics: audited divergent continuations (issue #259).

The replay-safety triad has three outcomes at the tool boundary. REPLAY
exists (#237, ``protected_call`` returns the journalled result). REJECT
exists (the gate refuses unclaimed or uncertain effects). FORK did not:
when a restored agent legitimately re-plans and emits a call whose intent
genuinely differs from anything journalled, blocking it forever is wrong,
but executing it silently inside the original run hides the divergence.
Codex CLI ships context-only session forks with no durability; ACRFence
(arXiv:2603.20625) names replay-or-fork but never implemented it. This
module owns the third outcome, approval-first:

- :func:`detect_fork_candidates` recognises the interesting refusals. A
  gated call denied as unclaimed is a *fork candidate* when its resource
  tokens overlap a journalled action of the same type: the agent is
  redoing work it remembers under different parameters, which after a
  restore is exactly what legitimate divergence looks like. No overlap
  means an ordinary first-seen effect and no signal.
- :func:`approve_fork` executes an approved divergence: a linked child run
  (``parent_run_id``, reusing the #243 hierarchy) plus a ``RUN_FORKED``
  event on the parent log recording child, reason and divergence point.
  The parent chain stays append-only and untouched otherwise.

Approval-first is deliberate: automatic branching would let an injected
prompt steer topology silently. A human names the reason, and the reason
is the audit. Forks parent onto the named run; a fork of a fork is just a
deeper hierarchy, which the #243 roll-up already understands.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from continuum.actions.idempotency import identity_tokens
from continuum.events import EventType
from continuum.models import Action, Origin, Run
from continuum.storage.base import Storage

__all__ = ["ForkNeighbour", "detect_fork_candidates", "approve_fork"]


@dataclass(frozen=True)
class ForkNeighbour:
    """One journalled action the denied call resembles."""

    key: str
    action_id: str
    action_type: str
    status: str
    external_id: str | None
    shared_tokens: tuple[str, ...]


def _action_tokens(action: Action) -> frozenset[str]:
    return identity_tokens(
        arguments=dict(action.arguments or {}),
        external_id=action.external_id,
    )


def detect_fork_candidates(
    *,
    action_type: str,
    tool_input: Mapping[str, Any],
    actions_by_key: Mapping[str, Action],
) -> list[ForkNeighbour]:
    """Journalled same-type actions sharing a resource token with this call.

    Deterministic: candidates sort by (number of shared tokens desc, key),
    so identical ledgers yield identical refusal envelopes.
    """
    incoming = identity_tokens(arguments=dict(tool_input))
    if not incoming:
        return []

    neighbours: list[ForkNeighbour] = []
    for key, action in actions_by_key.items():
        if action.action_type != action_type:
            continue
        shared = tuple(sorted(incoming & _action_tokens(action)))
        if not shared:
            continue
        neighbours.append(
            ForkNeighbour(
                key=key,
                action_id=action.action_id,
                action_type=action.action_type,
                status=action.status.value,
                external_id=action.external_id,
                shared_tokens=shared,
            )
        )
    neighbours.sort(key=lambda n: (-len(n.shared_tokens), n.key))
    return neighbours


def approve_fork(
    storage: Storage,
    parent_run_id: str,
    *,
    reason: str,
    child_run_id: str | None = None,
) -> Run:
    """Create an approved divergent continuation of ``parent_run_id``.

    Writes ``RUN_FORKED`` to the parent log (Origin.HUMAN: a human approved
    this branch) and creates the linked child run with ``parent_run_id``
    set, so #243's aggregation and ``continuum tree`` see it without any new
    machinery. The child starts empty: it inherits nothing mutable from the
    parent, by the same rule that keeps siblings independent.
    """
    parent = storage.get_run(parent_run_id)
    if not reason or not reason.strip():
        raise ValueError("a fork needs a stated reason; the reason is the audit")

    from continuum.storage.base import RunNotFound

    if child_run_id is None:
        existing = {r.run_id for r in storage.list_runs(limit=None)}
        n = 1
        while True:
            candidate = f"{parent_run_id}_fork{n}"
            if candidate not in existing:
                child_run_id = candidate
                break
            n += 1
    else:
        try:
            storage.get_run(child_run_id)
        except RunNotFound:
            pass
        else:
            raise ValueError(f"run {child_run_id!r} already exists")

    latest = storage.latest_version(parent_run_id)
    divergence = latest.source_sequence if latest else 0

    child = Run(
        run_id=child_run_id,
        goal=parent.goal,
        parent_run_id=parent_run_id,
        metadata={
            "fork": "true",
            "fork_reason": reason.strip(),
            "fork_parent_sequence": divergence,
        },
    )
    storage.create_run(child)
    storage.append_event(
        parent_run_id,
        EventType.RUN_FORKED,
        {
            "child_run_id": child.run_id,
            "reason": reason.strip(),
            "divergence_sequence": divergence,
        },
        source=Origin.HUMAN,
    )
    return child
