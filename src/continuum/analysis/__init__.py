"""Source-level dependency ownership for localized recovery.

See :mod:`continuum.analysis.depends` for the implementation and the two
queries recovery scoping relies on: ``owner_of`` and ``files_using``.
"""

from continuum.analysis.depends import (
    DependencyGraph,
    _normalize_dep,
    _STDLIB,
)

__all__ = ["DependencyGraph", "_normalize_dep", "_STDLIB"]
