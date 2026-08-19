"""Plugin registry and capability seams for CONTINUUM.

A plugin is any object registered in a :class:`Registry` under a name, and
conforming to one of the four capability seams:

* :class:`~continuum.environment.EnvironmentProvider` (discover the world)
* :class:`StateExtractor` (map a framework's state onto CONTINUUM)
* :class:`ActionReconciler` (settle an uncertain side effect)
* :class:`ValidationRule` (domain-specific staleness)
"""

from continuum.plugins.registry import Registration, Registry
from continuum.plugins.seams import (
    ActionReconciler,
    EnvironmentProvider,
    Reconciliation,
    StateExtractor,
    ValidationRule,
)

__all__ = [
    "Registry",
    "Registration",
    "EnvironmentProvider",
    "StateExtractor",
    "ActionReconciler",
    "ValidationRule",
    "Reconciliation",
]
