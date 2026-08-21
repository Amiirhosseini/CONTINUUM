from continuum.dashboard import render_dashboard_html, render_run_detail_html
from continuum.events import EventType
from continuum.models import Run
from continuum.storage import SQLiteStorage


def test_dashboard_renders_runs() -> None:
    storage = SQLiteStorage(":memory:")
    storage.create_run(Run(run_id="run_1", goal="g"))
    storage.append_event("run_1", EventType.RUN_STARTED, {"goal": "g", "total": 1})
    html = render_dashboard_html(storage)
    assert "run_1" in html
    assert "CONTINUUM Dashboard" in html


def test_dashboard_empty_runs() -> None:
    storage = SQLiteStorage(":memory:")
    html = render_dashboard_html(storage)
    assert "No runs" in html


def test_dashboard_run_detail_shows_ledger_and_contract() -> None:
    storage = SQLiteStorage(":memory:")
    storage.create_run(Run(run_id="run_1", goal="g"))
    storage.append_event("run_1", EventType.RUN_STARTED, {"goal": "g", "total": 1})
    html = render_run_detail_html(storage, "run_1")
    assert "run_1" in html
    assert "Contract" in html
    assert "Validation" in html
