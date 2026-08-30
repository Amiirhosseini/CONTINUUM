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


def test_dashboard_pagination_hint_shows_for_many_events() -> None:
    storage = SQLiteStorage(":memory:")
    storage.create_run(Run(run_id="run_1", goal="g"))
    for i in range(30):
        storage.append_event("run_1", EventType.TOOL_CALLED, {"i": i})
    html = render_run_detail_html(storage, "run_1")
    assert "Showing last 20 of 30 events" in html
    assert "continuum events run_1" in html
    assert "for full log" in html


def test_dashboard_no_pagination_hint_for_few_events() -> None:
    storage = SQLiteStorage(":memory:")
    storage.create_run(Run(run_id="run_1", goal="g"))
    for i in range(5):
        storage.append_event("run_1", EventType.TOOL_CALLED, {"i": i})
    html = render_run_detail_html(storage, "run_1")
    assert "Showing last 20 of" not in html


def test_dashboard_no_pagination_hint_for_exactly_twenty() -> None:
    storage = SQLiteStorage(":memory:")
    storage.create_run(Run(run_id="run_1", goal="g"))
    for i in range(20):
        storage.append_event("run_1", EventType.TOOL_CALLED, {"i": i})
    html = render_run_detail_html(storage, "run_1")
    assert "Showing last 20 of" not in html
