"""Minimal dashboard over CONTINUUM runs.

Renders run state, validation outcomes, recovery contracts, and events as
HTML. It is a presentation layer only, using the same Storage, CheckpointManager
and RecoveryEngine the CLI uses.
"""

from __future__ import annotations

import html
import http.server
import socketserver
from typing import Any

from continuum.recovery import RecoveryEngine
from continuum.storage.base import Storage


def render_dashboard_html(storage: Storage) -> str:
    runs = storage.list_runs()
    rows: list[str] = []
    for run in runs:
        engine = RecoveryEngine(storage)
        try:
            decision = engine.assess(run.run_id)
            mode = html.escape(decision.mode.value)
            safe = "yes" if decision.safe else "no"
        except Exception as exc:
            mode = html.escape(f"error: {exc}")
            safe = "unknown"
        rows.append(
            f"<tr><td>{html.escape(run.run_id)}</td>"
            f"<td>{html.escape(run.status.value)}</td>"
            f"<td>{mode}</td><td>{safe}</td></tr>"
        )
    body = "\n".join(rows) if rows else "<tr><td colspan=4>No runs</td></tr>"
    return f"""<!doctype html>
<html><head><meta charset=\"utf-8\"><title>CONTINUUM Dashboard</title></head>
<body><h1>CONTINUUM Dashboard</h1>
<table border=\"1\" cellpadding=\"6\"><tr><th>Run</th><th>Status</th><th>Recovery</th><th>Safe</th></tr>
{body}
</table></body></html>"""


def render_run_detail_html(storage: Storage, run_id: str) -> str:
    try:
        run = storage.get_run(run_id)
    except Exception as exc:
        return f"""<!doctype html><html><body><h1>Run not found</h1><p>{html.escape(str(exc))}</p></body></html>"""
    engine = RecoveryEngine(storage)
    try:
        decision = engine.assess(run_id)
        contract_html = html.escape(decision.contract.model_dump_json(indent=2))
        validation_rows = "".join(
            f"<tr><td>{html.escape(e.component.value)}</td><td>{html.escape(e.status.value)}</td><td>{html.escape(e.detail or '')}</td></tr>"
            for e in decision.validation.report.statuses
        )
        ledger_html = f"<pre>{contract_html}</pre>"
        validation_html = f'<table border="1" cellpadding="4"><tr><th>Component</th><th>Status</th><th>Detail</th></tr>{validation_rows}</table>'
    except Exception as exc:
        ledger_html = f"<p>{html.escape(str(exc))}</p>"
        validation_html = ""
    events = storage.read_events(run_id)
    events_rows = "".join(
        f"<tr><td>{e.sequence}</td><td>{html.escape(e.type.value)}</td><td>{html.escape(str(e.payload))}</td></tr>"
        for e in events[-20:]
    )
    events_html = f'<table border="1" cellpadding="4"><tr><th>Seq</th><th>Type</th><th>Payload</th></tr>{events_rows}</table>'
    return f"""<!doctype html>
<html><head><meta charset=\"utf-8\"><title>Run {html.escape(run_id)}</title></head>
<body><h1>Run {html.escape(run_id)}</h1>
<p>Goal: {html.escape(run.goal)} | Status: {html.escape(run.status.value)}</p>
<h2>Contract</h2>{ledger_html}
<h2>Validation</h2>{validation_html}
<h2>Recent events</h2>{events_html}
<p><a href=\"/\">Back to dashboard</a></p></body></html>"""


def serve_dashboard(storage: Storage, port: int = 8000) -> None:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path.startswith("/runs/"):
                run_id = self.path.split("/runs/")[1].split("?")[0].split("/")[0]
                content = render_run_detail_html(storage, run_id)
            else:
                content = render_dashboard_html(storage)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"Serving dashboard at http://localhost:{port}")
        httpd.serve_forever()
