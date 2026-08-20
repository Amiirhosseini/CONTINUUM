from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from types import SimpleNamespace

import pytest

from continuum.concurrency import InMemoryLeaseCoordinator
from continuum.models import RecoveryContract, RecoverySafety
from continuum.recovery import (
    FileLedgerBackend,
    LedgerEntryKind,
    MemoryLedgerBackend,
    RecoveryLedger,
)


def _contract(
    version: int = 0, status: RecoverySafety = RecoverySafety.REQUIRES_REPAIR
) -> RecoveryContract:
    return RecoveryContract(run_id="run_1", checkpoint_version=version, recovery_status=status)


@pytest.fixture
def ledger() -> Iterator[RecoveryLedger]:
    yield RecoveryLedger(MemoryLedgerBackend())


def test_append_decision_chains_from_genesis(ledger: RecoveryLedger) -> None:
    entry = ledger.append_decision("run_1", _contract(0))
    assert entry.sequence == 0
    assert entry.prev_hash == "genesis"
    assert entry.kind == LedgerEntryKind.DECISION.value
    ok, trusted = ledger.verify("run_1")
    assert ok is True
    assert trusted == 1


def test_tampering_breaks_chain(ledger: RecoveryLedger) -> None:
    ledger.append_decision("run_1", _contract(0))
    ledger.append_decision("run_1", _contract(1))

    entries = ledger.entries("run_1")
    tampered = replace(entries[0], note="hacked")
    ledger._backend.replace("run_1", [tampered, entries[1]])

    ok, broken_at = ledger.verify("run_1")
    assert ok is False
    assert broken_at == 0


def test_compact_keeps_anchors_and_recent_and_stays_verifiable(ledger: RecoveryLedger) -> None:
    ledger.append_decision("run_1", _contract(0))  # plain, old
    ledger.append_decision("run_1", _contract(1), anchor=True)  # anchor, old
    ledger.append_decision("run_1", _contract(2))  # plain, old
    ledger.append_decision("run_1", _contract(3))  # newest
    ledger.append_decision("run_1", _contract(4))  # newest

    removed = ledger.compact("run_1", keep=2, keep_anchors=True)
    assert removed == 2

    kept_sequences = {e.sequence for e in ledger.entries("run_1")}
    assert kept_sequences == {1, 3, 4}
    ok, _ = ledger.verify("run_1")
    assert ok is True


def test_attempts_and_requires_human(ledger: RecoveryLedger) -> None:
    ledger.record_attempt("run_1")
    ledger.record_attempt("run_1")
    assert ledger.attempts("run_1") == 2
    assert ledger.requires_human("run_1", max_attempts=3) is False
    ledger.record_attempt("run_1")
    assert ledger.requires_human("run_1", max_attempts=3) is True


def test_human_gate_persists_and_clears_pending(ledger: RecoveryLedger) -> None:
    ledger.append_decision("run_1", _contract(), gate="required")
    assert ledger.pending_gate("run_1") is not None
    ledger.record_gate("run_1", "approved")
    assert ledger.pending_gate("run_1") is None


def test_reconcile_detects_version_drift(ledger: RecoveryLedger) -> None:
    ledger.append_decision("run_1", _contract(version=5))
    aligned = ledger.reconcile("run_1", SimpleNamespace(version=5))
    assert aligned.drift is False

    drifted = ledger.reconcile("run_1", SimpleNamespace(version=3))
    assert drifted.drift is True


def test_file_backend_round_trips(tmp_path) -> None:  # type: ignore[no-untyped-def]
    backend = FileLedgerBackend(str(tmp_path))
    RecoveryLedger(backend).append_decision("run_1", _contract(0))
    RecoveryLedger(backend).append_decision("run_1", _contract(1))

    reopened = RecoveryLedger(backend)
    assert len(reopened.entries("run_1")) == 2
    assert reopened.verify("run_1")[0] is True


def test_append_under_cross_process_lock() -> None:
    ledger = RecoveryLedger(MemoryLedgerBackend(), lock=InMemoryLeaseCoordinator())
    ledger.append_decision("run_1", _contract())
    assert len(ledger.entries("run_1")) == 1
