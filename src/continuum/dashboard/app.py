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


def serve_dashboard(storage: Storage, port: int = 8000) -> None:
    html_content = render_dashboard_html(storage)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html_content.encode("utf-8"))

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"Serving dashboard at http://localhost:{port}")
        httpd.serve_forever()
