"""Bounded recovery context.

When an agent resumes, it needs to be told what it was doing — but handing it
the transcript defeats the purpose. This module renders the *minimum sufficient
context*: what the goal is, what is verified, what is no longer trustworthy, and
what it is allowed to do next.

Two rules shape the output:

**Stale state is shown, not hidden.** A recovered agent that is not told its
dataset changed will confidently continue with invalid assumptions. Doubt is
part of the context.

**It fits in a budget.** Sections are rendered in priority order and truncated
from the least important end, so a large run degrades by dropping detail rather
than by blowing the context window.

Token counts here are *estimates* from a character heuristic, not a tokenizer.
CONTINUUM does not depend on a model provider, and pulling in a tokenizer for a
size hint would be a poor trade. The estimate is labelled as such everywhere it
appears, and the benchmark will measure real tokens when it measures anything.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from continuum.models import (
    ApprovalStatus,
    SemanticState,
    StateStatus,
)

__all__ = [
    "RecoveryContext",
    "ContextSection",
    "build_recovery_context",
    "estimate_tokens",
]

#: Rough characters-per-token. English prose sits near 4; structured text with
#: many short tokens sits lower. Used only for budgeting, never for billing.
_CHARS_PER_TOKEN = 4

_TERMINAL = frozenset({StateStatus.INVALID, StateStatus.STALE, StateStatus.CONFLICTED})


def estimate_tokens(text: str) -> int:
    """Approximate token count. A heuristic, not a tokenizer."""
    return max(1, round(len(text) / _CHARS_PER_TOKEN)) if text else 0


@dataclass(frozen=True, slots=True)
class ContextSection:
    """One titled block of the recovery context."""

    title: str
    lines: tuple[str, ...]
    priority: int
    """Lower is more important; high-priority sections survive truncation."""

    def render(self) -> str:
        if not self.lines:
            return ""
        body = "\n".join(f"  {line}" for line in self.lines)
        return f"{self.title}\n{body}"

    @property
    def estimated_tokens(self) -> int:
        return estimate_tokens(self.render())


@dataclass(frozen=True, slots=True)
class RecoveryContext:
    """The reconstructed briefing handed to a resuming agent."""

    run_id: str
    sections: tuple[ContextSection, ...] = ()
    dropped_sections: tuple[str, ...] = ()
    truncated: bool = False
    notes: tuple[str, ...] = field(default=())

    def render(self) -> str:
        blocks = [section.render() for section in self.sections if section.lines]
        text = "\n\n".join(blocks)
        if self.truncated:
            dropped = ", ".join(self.dropped_sections)
            text += f"\n\n[context truncated to fit budget; omitted: {dropped}]"
        return text

    @property
    def estimated_tokens(self) -> int:
        return estimate_tokens(self.render())

    def __str__(self) -> str:
        return self.render()


def _goal_section(state: SemanticState) -> ContextSection:
    lines = [f"{state.goal.description}  (goal v{state.goal.version})"]
    lines += [f"constraint: {c}" for c in state.goal.constraints]
    return ContextSection("CURRENT GOAL", tuple(lines), priority=0)


def _progress_section(state: SemanticState) -> ContextSection:
    p = state.progress
    total = "unknown" if p.total is None else str(p.total)
    line = f"{p.completed} completed, {p.pending} pending, {p.failed} failed (of {total})"
    lines = [line, f"derived from events 1..{state.source_sequence}"]
    return ContextSection("VERIFIED PROGRESS", tuple(lines), priority=1)


def _stale_section(state: SemanticState) -> ContextSection:
    """Everything the agent must not rely on. Highest priority after the goal."""
    lines: list[str] = []
    for decision in state.decisions:
        if decision.status in _TERMINAL:
            reason = decision.invalidated_reason or "no reason recorded"
            lines.append(f"[{decision.status}] decision {decision.decision_id}: {reason}")
    for finding in state.findings:
        if finding.status in _TERMINAL:
            lines.append(f"[{finding.status}] finding {finding.finding_id}: {finding.claim}")
    for dependency in state.external_dependencies:
        if dependency.status in _TERMINAL:
            lines.append(
                f"[{dependency.status}] dependency {dependency.resource} "
                f"(recorded version {dependency.version})"
            )
    for approval in state.approvals:
        if approval.status in (ApprovalStatus.EXPIRED, ApprovalStatus.REVOKED):
            lines.append(f"[{approval.status}] approval {approval.approval_id}: {approval.subject}")

    dangling = sorted(state.dangling_evidence())
    if dangling:
        lines.append(f"evidence cited but unavailable: {', '.join(dangling)}")

    return ContextSection("STALE STATE — DO NOT RELY ON", tuple(lines), priority=2)


def _review_section(state: SemanticState) -> ContextSection:
    """Inferred or unverified state that a human or a check must confirm."""
    lines = [
        f"[{d.status}] decision {d.decision_id}: {d.decision}"
        for d in state.decisions
        if d.status is StateStatus.REQUIRES_REVIEW
    ]
    lines += [
        f"[{f.status}] finding {f.finding_id}: {f.claim}"
        for f in state.findings
        if f.status is StateStatus.REQUIRES_REVIEW
    ]
    if state.model and state.model.model_specific_state:
        lines += [
            f"model-specific: {item.description} ({item.required_validation})"
            for item in state.model.model_specific_state
        ]
    return ContextSection("REQUIRES REVIEW", tuple(lines), priority=3)


def _decisions_section(state: SemanticState, limit: int) -> ContextSection:
    valid = state.valid_decisions()
    lines = [f"{d.decision_id}: {d.decision}" for d in valid[:limit]]
    if len(valid) > limit:
        lines.append(f"... and {len(valid) - limit} more valid decisions")
    return ContextSection("VALID DECISIONS", tuple(lines), priority=4)


def _pending_section(state: SemanticState, limit: int) -> ContextSection:
    work = state.open_work()
    lines = [f"{w.task_id}: {w.description}" for w in work[:limit]]
    if len(work) > limit:
        lines.append(f"... and {len(work) - limit} more pending tasks")
    return ContextSection("PENDING TASKS", tuple(lines), priority=5)


def _findings_section(state: SemanticState, limit: int) -> ContextSection:
    usable = [f for f in state.findings if f.status is StateStatus.VALID]
    ranked = sorted(usable, key=lambda f: (-f.confidence, f.finding_id))
    lines = [f"{f.finding_id} ({f.confidence:.2f}): {f.claim}" for f in ranked[:limit]]
    if len(ranked) > limit:
        lines.append(f"... and {len(ranked) - limit} more findings")
    return ContextSection("RELEVANT FINDINGS", tuple(lines), priority=6)


def _dependencies_section(state: SemanticState) -> ContextSection:
    lines = [
        f"{d.resource}: {d.version or 'unversioned'} [{d.status}]"
        for d in state.external_dependencies
        if d.status not in _TERMINAL
    ]
    return ContextSection("EXTERNAL DEPENDENCIES", tuple(lines), priority=7)


def build_recovery_context(
    state: SemanticState,
    *,
    token_budget: int | None = None,
    max_items: int = 10,
    next_action: str | None = None,
    environment_changes: Sequence[str] = (),
) -> RecoveryContext:
    """Assemble a bounded briefing for a resuming agent.

    Sections are dropped from the least important end when a budget is given.
    The goal, verified progress and stale state are never dropped: an agent that
    resumes without knowing what it must distrust is worse than one that does
    not resume at all.
    """
    sections = [
        _goal_section(state),
        _progress_section(state),
        _stale_section(state),
        _review_section(state),
        _decisions_section(state, max_items),
        _pending_section(state, max_items),
        _findings_section(state, max_items),
        _dependencies_section(state),
    ]

    if environment_changes:
        sections.append(
            ContextSection("ENVIRONMENT CHANGES", tuple(environment_changes), priority=2)
        )
    if next_action:
        sections.append(ContextSection("NEXT SAFE ACTION", (next_action,), priority=0))

    populated = [s for s in sections if s.lines]
    populated.sort(key=lambda s: s.priority)

    if token_budget is None:
        return RecoveryContext(run_id=state.run_id, sections=tuple(populated))

    kept: list[ContextSection] = []
    dropped: list[str] = []
    protected = 3  # goal, progress, stale state are never sacrificed

    for index, section in enumerate(populated):
        candidate = RecoveryContext(run_id=state.run_id, sections=(*kept, section))
        if candidate.estimated_tokens <= token_budget or index < protected:
            kept.append(section)
        else:
            dropped.append(section.title)

    return RecoveryContext(
        run_id=state.run_id,
        sections=tuple(kept),
        dropped_sections=tuple(dropped),
        truncated=bool(dropped),
    )
