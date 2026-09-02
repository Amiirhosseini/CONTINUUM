"""Wrapper for provenance graph (compatibility, issue #552)."""

from continuum.provenance.graph import (
    ProvenanceGraph,
    ProvenanceNode,
    build_provenance_graph,
    downstream_of,
)

__all__ = ["ProvenanceGraph", "ProvenanceNode", "build_provenance_graph", "downstream_of"]
