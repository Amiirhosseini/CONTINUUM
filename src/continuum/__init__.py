"""CONTINUUM — verifiable semantic recovery layer for long-running AI agents.

Agents that can lose their context without losing their work.

Phase 1 exposes the durable data model and the append-only event log. The
runtime (``Continuum``), storage engines, validation, action ledger and CLI
arrive in later phases; nothing here imports an LLM provider.
"""

from continuum.events import (
    AppendOnlyViolation,
    Event,
    EventLog,
    EventType,
    IntegrityReport,
    IntegrityViolation,
)
from continuum.models import (
    Action,
    ActionStatus,
    Approval,
    ApprovalStatus,
    Component,
    ComponentValidationEntry,
    Decision,
    DiffEntry,
    DiffKind,
    EnvironmentSnapshot,
    EnvResource,
    Evidence,
    Finding,
    Goal,
    ModelSpecificState,
    ModelState,
    PendingWork,
    PlanStep,
    PlanStepStatus,
    Progress,
    RecoveryContract,
    RecoveryMode,
    RecoverySafety,
    RunStatus,
    SemanticState,
    StateCheckpoint,
    StateDiff,
    StateStatus,
    StateValidationResult,
    UnknownSideEffect,
    utcnow,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # events
    "AppendOnlyViolation",
    "Event",
    "EventLog",
    "EventType",
    "IntegrityReport",
    "IntegrityViolation",
    # enums
    "ActionStatus",
    "ApprovalStatus",
    "Component",
    "DiffKind",
    "PlanStepStatus",
    "RecoveryMode",
    "RecoverySafety",
    "RunStatus",
    "StateStatus",
    # state
    "Action",
    "Approval",
    "ComponentValidationEntry",
    "Decision",
    "DiffEntry",
    "EnvResource",
    "EnvironmentSnapshot",
    "Evidence",
    "Finding",
    "Goal",
    "ModelSpecificState",
    "ModelState",
    "PendingWork",
    "PlanStep",
    "Progress",
    "RecoveryContract",
    "SemanticState",
    "StateCheckpoint",
    "StateDiff",
    "StateValidationResult",
    "UnknownSideEffect",
    "utcnow",
]
