"""Canonical provenance vocabulary for CONTINUUM.

CONTINUUM tracks three *orthogonal* provenance axes. They answer different
questions and must not be collapsed into one flat enum without losing
information:

* :class:`~continuum.models.Origin` (``who``)       -- who/what asserted the fact
* :class:`~continuum.security.provenance.TrustLevel` (``how``) -- how trusted/verified the claim is
* :class:`~continuum.models.StateStatus` (``what``)  -- the current validity state of the fact

This module introduces a *derived, normalized* surface vocabulary
(:class:`CanonicalProvenance`) that maps each axis to a common, externally
meaningful label set::

    AGENT_ASSERTED, OBSERVED, VERIFIED, INFERRED,
    STALE, CONTRADICTED, UNKNOWN, REQUIRES_REVIEW

The canonical labels are a **view**, not a replacement. The original enums
remain authoritative and are never deleted; :class:`ProvenanceView` carries all
three source values alongside their canonical projections, so no information is
lost. Where a canonical label necessarily merges two source distinctions (for
example :attr:`~continuum.models.StateStatus.EXPIRED` has no dedicated canonical
member and maps to ``STALE``), the original value is preserved in the source
enum and the mapping is documented below.

Mapping tables (auditable, and reversible in intent)::

    Origin (who)                 -> canonical
      DETERMINISTIC             -> OBSERVED   (recorded by trusted local code)
      HUMAN                     -> VERIFIED   (a person asserted it)
      LLM                       -> AGENT_ASSERTED
      EXTERNAL_AGENT            -> AGENT_ASSERTED
      IMPORTED                  -> INFERRED    (foreign checkpoint, no history)

    TrustLevel (how)             -> canonical
      verified                  -> VERIFIED
      unverified                -> INFERRED
      contested                 -> CONTRADICTED

    StateStatus (what)           -> canonical
      VALID                     -> VERIFIED
      STALE                     -> STALE
      CONFLICTED                -> CONTRADICTED
      UNKNOWN                   -> UNKNOWN
      INVALID                   -> CONTRADICTED
      REQUIRES_REVIEW           -> REQUIRES_REVIEW
      EXPIRED                   -> STALE  (original StateStatus.EXPIRED retained)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from continuum.models import Origin, StateStatus
from continuum.security.provenance import TrustLevel


class CanonicalProvenance(StrEnum):
    """Normalized, externally meaningful provenance labels.

    A single flat enum cannot faithfully represent three orthogonal axes, so
    these labels are axis-agnostic surface terms. Always read them together
    with the source axis they came from (see :class:`ProvenanceView`).
    """

    AGENT_ASSERTED = "agent_asserted"
    OBSERVED = "observed"
    VERIFIED = "verified"
    INFERRED = "inferred"
    STALE = "stale"
    CONTRADICTED = "contradicted"
    UNKNOWN = "unknown"
    REQUIRES_REVIEW = "requires_review"


#: ``who`` asserted a fact -> canonical label.
_ORIGIN_MAP: dict[Origin, CanonicalProvenance] = {
    Origin.DETERMINISTIC: CanonicalProvenance.OBSERVED,
    Origin.HUMAN: CanonicalProvenance.VERIFIED,
    Origin.LLM: CanonicalProvenance.AGENT_ASSERTED,
    Origin.EXTERNAL_AGENT: CanonicalProvenance.AGENT_ASSERTED,
    Origin.IMPORTED: CanonicalProvenance.INFERRED,
}

#: ``how`` trusted a claim is -> canonical label.
_TRUST_MAP: dict[TrustLevel, CanonicalProvenance] = {
    "verified": CanonicalProvenance.VERIFIED,
    "unverified": CanonicalProvenance.INFERRED,
    "contested": CanonicalProvenance.CONTRADICTED,
}

#: ``what`` validity state a fact is in -> canonical label.
_STATE_MAP: dict[StateStatus, CanonicalProvenance] = {
    StateStatus.VALID: CanonicalProvenance.VERIFIED,
    StateStatus.STALE: CanonicalProvenance.STALE,
    StateStatus.CONFLICTED: CanonicalProvenance.CONTRADICTED,
    StateStatus.UNKNOWN: CanonicalProvenance.UNKNOWN,
    StateStatus.INVALID: CanonicalProvenance.CONTRADICTED,
    StateStatus.REQUIRES_REVIEW: CanonicalProvenance.REQUIRES_REVIEW,
    # No dedicated canonical member: EXPIRED is "validity lapsed by time" and is
    # treated as a stale claim. StateStatus.EXPIRED is preserved in the source
    # enum, so the distinction is not destroyed -- it is only normalized away at
    # the surface.
    StateStatus.EXPIRED: CanonicalProvenance.STALE,
}


def canonical_origin(origin: Origin) -> CanonicalProvenance:
    """Map *who* asserted a fact to its canonical label."""
    return _ORIGIN_MAP[origin]


def canonical_trust(level: TrustLevel) -> CanonicalProvenance:
    """Map *how trusted* a claim is to its canonical label."""
    return _TRUST_MAP[level]


def canonical_state_status(status: StateStatus) -> CanonicalProvenance:
    """Map *what validity state* a fact is in to its canonical label."""
    return _STATE_MAP[status]


@dataclass(frozen=True)
class ProvenanceView:
    """An information-preserving projection of provenance.

    Carries the three authoritative source values and their canonical labels.
    ``primary`` picks the single most decision-relevant label: the validity
    state when the fact is not plainly valid, otherwise trust, otherwise who.
    """

    origin: Origin
    state_status: StateStatus
    trust: TrustLevel | None = None

    @property
    def who(self) -> CanonicalProvenance:
        return canonical_origin(self.origin)

    @property
    def how_trusted(self) -> CanonicalProvenance:
        if self.trust is None:
            # Absent trust information is not the same as a known-untrusted
            # claim; the source value (None) is preserved on the view.
            return CanonicalProvenance.UNKNOWN
        return canonical_trust(self.trust)

    @property
    def what_state(self) -> CanonicalProvenance:
        return canonical_state_status(self.state_status)

    @property
    def primary(self) -> CanonicalProvenance:
        if self.state_status is not StateStatus.VALID:
            return self.what_state
        if self.trust is not None:
            return self.how_trusted
        return self.who


def summarize(
    origin: Origin,
    state_status: StateStatus,
    trust: TrustLevel | None = None,
) -> ProvenanceView:
    """Build a :class:`ProvenanceView` from the three source axes."""
    return ProvenanceView(origin=origin, state_status=state_status, trust=trust)


__all__ = [
    "CanonicalProvenance",
    "ProvenanceView",
    "canonical_origin",
    "canonical_state_status",
    "canonical_trust",
    "summarize",
]
