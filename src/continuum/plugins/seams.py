"""The four capability seams a plugin can implement.

Each seam is a ``Protocol`` (interface), with one or more providers
(implementations) and consumers inside CONTINUUM. Swapping a provider changes
behavior without changing call sites. See references/integration-architecture.md
section 3.2.

The ``EnvironmentProvider`` seam already ships in ``continuum.environment``;
it is re-exported here so all four seams live behind one import.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from continuum.environment import EnvironmentProvider
from continuum.models import (
    Action,
    ComponentValidationEntry,
    EnvironmentSnapshot,
    SemanticState,
)


@dataclass
class Reconciliation:
    """The outcome an ``ActionReconciler`` reports for an uncertain side effect."""

    occurred: bool
    external_id: str | None = None
    note: str = ""


@runtime_checkable
class StateExtractor(Protocol):
    """Maps an arbitrary framework's trajectory onto CONTINUUM's SemanticState."""

    name: str

    def extract(
        self, trajectory: Any, environment: EnvironmentSnapshot | None = None
    ) -> SemanticState: ...


@runtime_checkable
class ActionReconciler(Protocol):
    """Resolves an uncertain side effect using external evidence."""

    name: str

    def reconcile(self, action: Action) -> Reconciliation: ...


@runtime_checkable
class ValidationRule(Protocol):
    """Domain-specific staleness beyond environment changes."""

    name: str

    def evaluate(
        self, state: SemanticState, environment: EnvironmentSnapshot | None = None
    ) -> list[ComponentValidationEntry]: ...


__all__ = [
    "EnvironmentProvider",
    "StateExtractor",
    "ActionReconciler",
    "ValidationRule",
    "Reconciliation",
]
