"""DOT export and compaction survival for provenance graph (issue #554)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from continuum.events import EventType
from continuum.models import Run
from continuum.provenance.graph import build_provenance_graph, to_dot
from continuum.storage.sqlite import SQLiteStorage


def test_dot_export_contains_origin_colors():
    storage = SQLiteStorage(":memory:")
    run_id = "run_dot"
    storage.create_run(Run(run_id=run_id, goal="g"))
    ev = storage.append_event(run_id, EventType.EVIDENCE_ADDED, {"evidence_id": "ev1"})
    dec = storage.append_event(
        run_id,
        EventType.DECISION_CREATED,
        {"decision": "d", "decision_id": "dec1", "caused_by": [ev.event_id]},
    )
    graph = build_provenance_graph(storage.read_events(run_id))
    dot = to_dot(graph)
    assert "digraph provenance" in dot
    assert ev.event_id in dot
    assert dec.event_id in dot
    # Origin colors: deterministic should be lightblue
    assert "lightblue" in dot or "orange" in dot or "lightgreen" in dot
    # Edges
    assert f'"{ev.event_id}" -> "{dec.event_id}"' in dot


def test_graph_survives_compaction_via_archive():
    # Create a run, build graph, compact, reopen, graph still same via read_all_events
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "comp.db"
        storage = SQLiteStorage(str(db))
        run_id = "run_compact"
        storage.create_run(Run(run_id=run_id, goal="g"))
        ev = storage.append_event(run_id, EventType.EVIDENCE_ADDED, {"evidence_id": "ev1"})
        dec = storage.append_event(
            run_id,
            EventType.DECISION_CREATED,
            {"decision": "d", "decision_id": "dec1", "caused_by": [ev.event_id]},
        )
        storage.append_event(
            run_id,
            EventType.ACTION_RECORDED,
            {"action_type": "send", "action_id": "act1", "caused_by": [dec.event_id]},
        )
        # Need at least one checkpoint for compaction to have something to anchor
        from continuum.state.semantic import project

        state = project(run_id, storage.read_events(run_id))
        storage.put_version(state)
        # Build graph before compact
        graph_before = build_provenance_graph(storage.read_all_events(run_id))
        edges_before = {(p, c) for p, cs in graph_before.edges.items() for c in cs}
        # Compact
        report = storage.compact_run(run_id)
        assert report["archived"] >= 1
        # After compact, live events should be only anchor
        live = storage.read_events(run_id)
        assert any(e.type == EventType.EVENT_LOG_ANCHORED for e in live)
        # But read_all should still have full history
        all_events = storage.read_all_events(run_id)
        graph_after = build_provenance_graph(all_events)
        edges_after = {(p, c) for p, cs in graph_after.edges.items() for c in cs}
        assert edges_before == edges_after
        assert len(graph_after.nodes) == len(graph_before.nodes)
        # Also test CLI still works after compact
        storage.close()
        # Reopen and test CLI via subprocess
        db_str = str(db)
        cmd = [
            sys.executable,
            "-m",
            "continuum.cli",
            "--db",
            db_str,
            "--json",
            "provenance",
            run_id,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert len(payload["nodes"]) == len(graph_before.nodes)
        # Impact should also still work
        cmd2 = [
            sys.executable,
            "-m",
            "continuum.cli",
            "--db",
            db_str,
            "--json",
            "impact",
            run_id,
            "--evidence",
            ev.event_id,
        ]
        result2 = subprocess.run(cmd2, capture_output=True, text=True)
        assert result2.returncode == 0, result2.stderr
        payload2 = json.loads(result2.stdout)
        assert any(n["event_id"] == dec.event_id for n in payload2["downstream"])
        # DOT export after compact
        cmd3 = [
            sys.executable,
            "-m",
            "continuum.cli",
            "--db",
            db_str,
            "provenance",
            run_id,
            "--dot",
        ]
        result3 = subprocess.run(cmd3, capture_output=True, text=True)
        assert result3.returncode == 0, result3.stderr
        assert "digraph provenance" in result3.stdout
        assert ev.event_id in result3.stdout
