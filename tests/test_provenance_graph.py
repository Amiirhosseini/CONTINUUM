"""Provenance DAG projector tests (issue #552)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from continuum.events import EventType
from continuum.models import Run
from continuum.provenance.graph import build_provenance_graph, downstream_of
from continuum.storage.sqlite import SQLiteStorage


# Use CLI helper from tests
def _run(*args: str, db: str | None = None):
    """Helper to run continuum CLI via subprocess."""
    cmd = (
        [sys.executable, "-m", "continuum.cli", "--db", db] + list(args)
        if db
        else [sys.executable, "-m", "continuum.cli"] + list(args)
    )
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def test_build_graph_with_caused_by_edges():
    storage = SQLiteStorage(":memory:")
    run_id = "run_prov_1"
    storage.create_run(Run(run_id=run_id, goal="test"))
    ev = storage.append_event(
        run_id, EventType.EVIDENCE_ADDED, {"evidence_id": "ev1", "summary": "s"}
    )
    _find = storage.append_event(
        run_id, EventType.FINDING_ADDED, {"finding_id": "f1", "claim": "c", "evidence": ["ev1"]}
    )
    # decision caused by evidence
    dec = storage.append_event(
        run_id,
        EventType.DECISION_CREATED,
        {"decision": "d1", "decision_id": "dec1", "caused_by": [ev.event_id]},
    )
    # action caused by decision
    act = storage.append_event(
        run_id,
        EventType.ACTION_RECORDED,
        {"action_type": "send", "action_id": "act1", "caused_by": [dec.event_id]},
    )
    events = storage.read_events(run_id)
    graph = build_provenance_graph(events)
    assert len(graph.nodes) == 4
    # edges: ev -> dec, dec -> act
    assert act.event_id in graph.edges.get(dec.event_id, [])
    assert dec.event_id in graph.edges.get(ev.event_id, [])
    # downstream of ev should include dec and act (transitive)
    downstream = graph.downstream(ev.event_id)
    assert dec.event_id in downstream
    assert act.event_id in downstream
    # downstream via helper
    ds_nodes = downstream_of(graph, ev.event_id)
    assert any(n.event_id == dec.event_id for n in ds_nodes)
    assert any(n.event_id == act.event_id for n in ds_nodes)


def test_downstream_via_payload_evidence_id():
    storage = SQLiteStorage(":memory:")
    run_id = "run_prov_2"
    storage.create_run(Run(run_id=run_id, goal="g"))
    ev = storage.append_event(run_id, EventType.EVIDENCE_ADDED, {"evidence_id": "ev_payload_1"})
    dec = storage.append_event(
        run_id,
        EventType.DECISION_CREATED,
        {"decision": "d", "decision_id": "dec2", "caused_by": [ev.event_id]},
    )
    events = storage.read_events(run_id)
    graph = build_provenance_graph(events)
    # downstream via payload evidence_id "ev_payload_1"
    ds = downstream_of(graph, "ev_payload_1")
    assert any(n.event_id == dec.event_id for n in ds)


def test_graph_nodes_carry_origin():
    storage = SQLiteStorage(":memory:")
    run_id = "run_prov_origin"
    storage.create_run(Run(run_id=run_id, goal="g"))
    ev = storage.append_event(run_id, EventType.EVIDENCE_ADDED, {"evidence_id": "ev1"})
    storage.append_event(
        run_id, EventType.DECISION_CREATED, {"decision": "d", "caused_by": [ev.event_id]}
    )
    graph = build_provenance_graph(storage.read_events(run_id))
    for node in graph.nodes.values():
        assert node.origin is not None
        assert node.origin.value in ("deterministic", "external_agent", "human", "llm", "imported")


def test_cli_provenance_json(tmp_path: Path):
    db = str(tmp_path / "prov.db")
    storage = SQLiteStorage(db)
    run_id = "run_cli_prov"
    storage.create_run(Run(run_id=run_id, goal="g"))
    ev = storage.append_event(run_id, EventType.EVIDENCE_ADDED, {"evidence_id": "ev1"})
    storage.append_event(
        run_id, EventType.DECISION_CREATED, {"decision": "d", "caused_by": [ev.event_id]}
    )
    storage.close()
    code, out, err = _run("provenance", run_id, "--json", db=db)
    # try alternative helper if above fails
    if code != 0:
        # Use test_cli run helper with db param
        import subprocess

        result = subprocess.run(
            [sys.executable, "-m", "continuum.cli", "--db", db, "--json", "provenance", run_id],
            capture_output=True,
            text=True,
        )
        code, out = result.returncode, result.stdout
    assert code == 0, err
    payload = json.loads(out)
    assert payload["run_id"] == run_id
    assert "nodes" in payload
    assert len(payload["nodes"]) >= 2
    for n in payload["nodes"]:
        assert "origin" in n
        assert "event_id" in n


def test_cli_impact_json(tmp_path: Path):
    db = str(tmp_path / "impact.db")
    storage = SQLiteStorage(db)
    run_id = "run_cli_impact"
    storage.create_run(Run(run_id=run_id, goal="g"))
    ev = storage.append_event(run_id, EventType.EVIDENCE_ADDED, {"evidence_id": "ev1"})
    dec = storage.append_event(
        run_id, EventType.DECISION_CREATED, {"decision": "d", "caused_by": [ev.event_id]}
    )
    storage.close()
    code, out, err = _run("impact", run_id, "--evidence", ev.event_id, "--json", db=db)
    if code != 0:
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "continuum.cli",
                "--db",
                db,
                "--json",
                "impact",
                run_id,
                "--evidence",
                ev.event_id,
            ],
            capture_output=True,
            text=True,
        )
        code, out = result.returncode, result.stdout
    assert code == 0, err
    payload = json.loads(out)
    assert payload["evidence"] == ev.event_id
    assert any(n["event_id"] == dec.event_id for n in payload["downstream"])
