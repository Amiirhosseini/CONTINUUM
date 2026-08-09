"""Semantic state: projection, extraction, versioning and diffing."""

from continuum.state.diff import diff_states, render_diff
from continuum.state.extractor import (
    CompositeExtractor,
    DeterministicExtractor,
    ExtractionContext,
    LLMExtractor,
    StateExtractor,
)
from continuum.state.semantic import ProjectionError, project, project_incremental
from continuum.state.versioning import VersionChain, VersionEntry

__all__ = [
    "CompositeExtractor",
    "DeterministicExtractor",
    "ExtractionContext",
    "LLMExtractor",
    "ProjectionError",
    "StateExtractor",
    "VersionChain",
    "VersionEntry",
    "diff_states",
    "project",
    "project_incremental",
    "render_diff",
]
