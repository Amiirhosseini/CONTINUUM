"""Multi-agent hierarchies: parents, children, aggregated contracts (#243).

A child run is an ordinary run whose parent_run_id points at its supervisor.
The parent resume composes the family worst state: no RESUME while any
non-terminal child holds uncertainty or requires review. Siblings share
nothing mutable - coordination lives in the ledger and contracts.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from continuum.actions import ActionLedger
from continuum.actions.idempotency import idempotency_key
from continuum.cli import ExitCode, main
from continuum.storage import SQLiteStorage


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = main(list(argv), out=out, err=err)
    return code, out.getvalue(), err.getvalue()


@pytest.fixture
def db(tmp_path: Path) -> str:
    return str(tmp_path / "fam.db")


def test_start_refuses_an_unknown_parent(db: str) -> None:
    code, _, err = run("--db", db, "start", "kid", "--goal", "k", "--parent", "ghost")
    assert code == ExitCode.NOT_FOUND
    assert "does not exist" in err


def test_completed_parent_cannot_grow_children(db: str) -> None:
    run("--db", db, "start", "par", "--goal", "p")
    run("--db", db, "complete", "par", "--summary", "done")
    code, _, err = run("--db", db, "start", "kid", "--goal", "k", "--parent", "par")
    assert code == ExitCode.ERROR
    assert "completed" in err


def test_children_record_their_parent(db: str) -> None:
    run("--db", db, "start", "par", "--goal", "supervise")
    run("--db", db, "start", "kid", "--goal", "work", "--parent", "par")
    with SQLiteStorage(db) as store:
        assert store.get_run("kid").parent_run_id == "par"
        assert store.get_run("par").parent_run_id is None


def test_a2a_task_id_lands_in_metadata(db: str) -> None:
    run("--db", db, "start", "worker", "--goal", "w", "--a2a-task", "a2a-task-42")
    with SQLiteStorage(db) as store:
        meta = store.get_run("worker").metadata
    assert meta.get("a2a_task_id") == "a2a-task-42"


def test_tree_lists_children(db: str) -> None:
    run("--db", db, "start", "boss", "--goal", "supervise")
    run("--db", db, "start", "kid_ok", "--goal", "fine", "--parent", "boss")
    code, out, _ = run("--db", db, "tree", "boss")
    assert code == ExitCode.OK
    assert "boss" in out and "kid_ok" in out


def test_uncertain_child_blocks_the_parent_resume(db: str) -> None:
    """The acceptance core: parent alone would RESUME; an uncertain child
    forces request_human. Settling the child unblocks the family."""
    run("--db", db, "start", "par", "--goal", "supervise")
    run("--db", db, "start", "kid", "--goal", "work", "--parent", "par")
    ledger = ActionLedger(SQLiteStorage(db), "kid")
    ledger.claim("send_invoice", {}, key="invoice:I-9")

    code, out, _ = run("--db", db, "--json", "resume", "par")
    payload = json.loads(out)
    assert payload["mode"] == "request_human"
    assert any("kid" in r for r in payload.get("family_rationale", []))

    key = idempotency_key("send_invoice", None, scope="kid", key="invoice:I-9")
    ActionLedger(SQLiteStorage(db), "kid").reconcile(str(key), occurred=True)
    code, out, _ = run("--db", db, "--json", "resume", "par")
    payload = json.loads(out)
    assert payload["safe"] is True


def test_clean_children_do_not_block_the_parent(db: str) -> None:
    run("--db", db, "start", "par", "--goal", "supervise")
    code, out, _ = run("--db", db, "--json", "resume", "par")
    payload = json.loads(out)
    assert payload["safe"] is True
