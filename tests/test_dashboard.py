import contextlib
import http.client
import os
import threading
import urllib.parse
from pathlib import Path

from continuum.dashboard import render_dashboard_html, render_run_detail_html
from continuum.dashboard.app import (
    DASHBOARD_DRAIN_LIMIT_BYTES,
    MAX_DASHBOARD_BODY,
    make_dashboard_server,
)
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


def test_dashboard_pagination_hint_includes_archived_after_compaction() -> None:
    """After compaction the hint must count archived events (Refs #520).

    Before the fix total = len(live) so a run with 20 live but 80 archived
    showed no hint even though the full log is 100. The fix counts both.
    """
    import html as html_lib

    # Use html-sensitive run_id to verify escaping in the hint.
    run_id = "run<1>&test"
    storage = SQLiteStorage(":memory:")
    storage.create_run_started(Run(run_id=run_id, goal="g"))
    # 98 total before compact: 1 RUN_STARTED + 97 TOOL_CALLED
    for i in range(97):
        storage.append_event(run_id, EventType.TOOL_CALLED, {"i": i})
    assert len(storage.read_events(run_id)) == 98
    assert len(storage.read_archived_events(run_id)) == 0
    # Compact so 80 archived, 20 live (18 tail + 2 anchor/checkpoint), 100 total.
    storage.compact_run(run_id, through_sequence=80)
    live = len(storage.read_events(run_id))
    archived = len(storage.read_archived_events(run_id))
    assert archived == 80
    assert live == 20
    assert live + archived == 100
    html = render_run_detail_html(storage, run_id)
    # Hint must show combined total, not just live (20 would be no hint).
    assert "Showing last 20 of 100 events" in html
    # HTML-escaped: run_id in hint is escaped, raw <>& must not appear.
    assert html_lib.escape(run_id) in html
    assert f"continuum events {html_lib.escape(run_id)} for full log" in html
    # Old logic would have computed total = live = 20 and shown no hint.
    assert live == 20


def test_dashboard_no_hint_for_fifteen_events_no_compact() -> None:
    """15 events with no anchor must not show the hint (Refs #520)."""
    storage = SQLiteStorage(":memory:")
    storage.create_run_started(Run(run_id="run_15", goal="g"))
    for i in range(14):
        storage.append_event("run_15", EventType.TOOL_CALLED, {"i": i})
    assert len(storage.read_events("run_15")) == 15
    assert len(storage.read_archived_events("run_15")) == 0
    html = render_run_detail_html(storage, "run_15")
    assert "Showing last 20 of" not in html


def test_dashboard_no_hint_for_twenty_exact_no_compact() -> None:
    """Exactly 20 combined events must not show the hint (Refs #520)."""
    storage = SQLiteStorage(":memory:")
    storage.create_run_started(Run(run_id="run_20", goal="g"))
    for i in range(19):
        storage.append_event("run_20", EventType.TOOL_CALLED, {"i": i})
    assert len(storage.read_events("run_20")) == 20
    html = render_run_detail_html(storage, "run_20")
    assert "Showing last 20 of" not in html


def test_dashboard_hint_for_twenty_one_with_one_archived() -> None:
    """21 combined (20 live + 1 archived) must show hint for 21 (Refs #520)."""
    run_id = "run_21"
    storage = SQLiteStorage(":memory:")
    storage.create_run_started(Run(run_id=run_id, goal="g"))
    for i in range(18):
        storage.append_event(run_id, EventType.TOOL_CALLED, {"i": i})
    assert len(storage.read_events(run_id)) == 19
    # Compact 1 archived, leaving 20 live (18 tail + 2 system) + 1 archived = 21 total.
    storage.compact_run(run_id, through_sequence=1)
    live = len(storage.read_events(run_id))
    archived = len(storage.read_archived_events(run_id))
    assert archived == 1
    assert live == 20
    assert live + archived == 21
    html = render_run_detail_html(storage, run_id)
    assert "Showing last 20 of 21 events" in html
    assert f"continuum events {run_id} for full log" in html


def test_dashboard_post_body_too_large_returns_413(tmp_path: Path) -> None:
    """Large POST bodies are refused with 413, matching gateway pattern (#317)."""
    # token needed for the small-body control, but the oversize check happens before auth
    os.environ["CONTINUUM_DASHBOARD_TOKEN"] = "op-secret"
    db = str(tmp_path / "dash.db")
    with SQLiteStorage(db) as store:
        store.create_run(Run(run_id="run_1", goal="g"))
        store.append_event("run_1", EventType.RUN_STARTED, {"goal": "g"})

    server = make_dashboard_server(SQLiteStorage(db), port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    addr = f"127.0.0.1:{server.server_address[1]}"
    try:
        # Oversize: 1 MB + 1, like the repro in #317 (6 MB would also work but is slower).
        huge = "x" * (MAX_DASHBOARD_BODY + 1)
        body = urllib.parse.urlencode(
            {"run_id": "run_1", "token": "op-secret", "blob": huge}
        ).encode()
        conn = http.client.HTTPConnection(addr, timeout=10)
        conn.request(
            "POST", "/action/reconcile", body=body, headers={"Content-Length": str(len(body))}
        )
        resp = conn.getresponse()
        data = resp.read().decode(errors="ignore")
        conn.close()
        assert resp.status == 413
        assert "Body too large" in data
        assert str(MAX_DASHBOARD_BODY) in data

        # Drain limit is the same bound the gateway uses, so behaviour is consistent.
        from continuum.gateway import DRAIN_LIMIT_BYTES

        assert DASHBOARD_DRAIN_LIMIT_BYTES == DRAIN_LIMIT_BYTES

        # Small body still succeeds (control): a valid confirm with a tiny payload.
        small_body = urllib.parse.urlencode({"run_id": "run_1", "token": "op-secret"}).encode()
        conn = http.client.HTTPConnection(addr, timeout=10)
        conn.request(
            "POST",
            "/action/confirm",
            body=small_body,
            headers={"Content-Length": str(len(small_body))},
        )
        resp = conn.getresponse()
        data = resp.read().decode(errors="ignore")
        conn.close()
        assert resp.status == 200
        assert "goal and progress confirmed" in data
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        os.environ.pop("CONTINUUM_DASHBOARD_TOKEN", None)


def _raw_dashboard_request(addr: str, raw: bytes) -> tuple[int, bytes]:
    """Send raw bytes and return (status, body) for the dashboard."""
    import socket

    host, port = addr.split(":")
    sock = socket.create_connection((host, int(port)), timeout=10)
    sock.sendall(raw)
    sock.settimeout(5)
    data = b""
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
    except OSError:
        pass
    finally:
        with contextlib.suppress(OSError):
            sock.close()
    if not data:
        return 0, b""
    header, _, body = data.partition(b"\r\n\r\n")
    first = header.split(b"\r\n")[0].decode(errors="ignore")
    try:
        status = int(first.split()[1])
    except Exception:
        status = 0
    return status, body


def test_dashboard_malformed_content_length_returns_400(tmp_path: Path) -> None:
    """Malformed Content-Length must yield 400 html, not a dropped connection (#522)."""
    os.environ["CONTINUUM_DASHBOARD_TOKEN"] = "op-secret"
    db = str(tmp_path / "dash.db")
    with SQLiteStorage(db) as store:
        store.create_run(Run(run_id="run_1", goal="g"))
        store.append_event("run_1", EventType.RUN_STARTED, {"goal": "g"})
    server = make_dashboard_server(SQLiteStorage(db), port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    addr = f"127.0.0.1:{server.server_address[1]}"
    try:
        raw = (
            b"POST /action/confirm HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Length: abc\r\n"
            b"Content-Type: application/x-www-form-urlencoded\r\n"
            b"Connection: close\r\n\r\n"
            b"run_id=run_1&token=op-secret"
        )
        status, body = _raw_dashboard_request(addr, raw)
        assert status == 400, f"expected 400, got {status} body={body!r}"
        assert b"invalid Content-Length" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        os.environ.pop("CONTINUUM_DASHBOARD_TOKEN", None)


def test_dashboard_negative_content_length_returns_400(tmp_path: Path) -> None:
    """Negative Content-Length is malformed (#522)."""
    os.environ["CONTINUUM_DASHBOARD_TOKEN"] = "op-secret"
    db = str(tmp_path / "dash.db")
    with SQLiteStorage(db) as store:
        store.create_run(Run(run_id="run_1", goal="g"))
        store.append_event("run_1", EventType.RUN_STARTED, {"goal": "g"})
    server = make_dashboard_server(SQLiteStorage(db), port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    addr = f"127.0.0.1:{server.server_address[1]}"
    try:
        raw = (
            b"POST /action/confirm HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Length: -1\r\n"
            b"Content-Type: application/x-www-form-urlencoded\r\n"
            b"Connection: close\r\n\r\n"
        )
        status, body = _raw_dashboard_request(addr, raw)
        assert status == 400
        assert b"invalid Content-Length" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        os.environ.pop("CONTINUUM_DASHBOARD_TOKEN", None)


def test_dashboard_chunked_is_rejected_with_400(tmp_path: Path) -> None:
    """Chunked Transfer-Encoding must not bypass the 1 MB cap (#522)."""
    os.environ["CONTINUUM_DASHBOARD_TOKEN"] = "op-secret"
    db = str(tmp_path / "dash.db")
    with SQLiteStorage(db) as store:
        store.create_run(Run(run_id="run_1", goal="g"))
        store.append_event("run_1", EventType.RUN_STARTED, {"goal": "g"})
    server = make_dashboard_server(SQLiteStorage(db), port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    addr = f"127.0.0.1:{server.server_address[1]}"
    try:
        raw = (
            b"POST /action/confirm HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"Content-Type: application/x-www-form-urlencoded\r\n"
            b"Connection: close\r\n\r\n"
            b"1b\r\nrun_id=run_1&token=op-secret\r\n0\r\n\r\n"
        )
        status, body = _raw_dashboard_request(addr, raw)
        assert status == 400, f"expected 400 for chunked, got {status} body={body!r}"
        assert b"chunked" in body.lower()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        os.environ.pop("CONTINUUM_DASHBOARD_TOKEN", None)


def test_dashboard_chunked_comma_list_case_insensitive(tmp_path: Path) -> None:
    """Transfer-Encoding may be a comma list and case-insensitive (#522)."""
    os.environ["CONTINUUM_DASHBOARD_TOKEN"] = "op-secret"
    db = str(tmp_path / "dash.db")
    with SQLiteStorage(db) as store:
        store.create_run(Run(run_id="run_1", goal="g"))
        store.append_event("run_1", EventType.RUN_STARTED, {"goal": "g"})
    server = make_dashboard_server(SQLiteStorage(db), port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    addr = f"127.0.0.1:{server.server_address[1]}"
    try:
        raw = (
            b"POST /action/confirm HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Transfer-Encoding: gzip, Chunked\r\n"
            b"Content-Type: application/x-www-form-urlencoded\r\n"
            b"Connection: close\r\n\r\n"
            b"5\r\nhello\r\n0\r\n\r\n"
        )
        status, body = _raw_dashboard_request(addr, raw)
        assert status == 400
        assert b"chunked" in body.lower()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        os.environ.pop("CONTINUUM_DASHBOARD_TOKEN", None)


def test_dashboard_small_body_still_200(tmp_path: Path) -> None:
    """Valid small POST must still succeed (regression)."""
    os.environ["CONTINUUM_DASHBOARD_TOKEN"] = "op-secret"
    db = str(tmp_path / "dash.db")
    with SQLiteStorage(db) as store:
        store.create_run(Run(run_id="run_1", goal="g"))
        store.append_event("run_1", EventType.RUN_STARTED, {"goal": "g"})
    server = make_dashboard_server(SQLiteStorage(db), port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    addr = f"127.0.0.1:{server.server_address[1]}"
    try:
        small = urllib.parse.urlencode({"run_id": "run_1", "token": "op-secret"}).encode()
        conn = http.client.HTTPConnection(addr, timeout=10)
        conn.request(
            "POST", "/action/confirm", body=small, headers={"Content-Length": str(len(small))}
        )
        resp = conn.getresponse()
        data = resp.read().decode(errors="ignore")
        conn.close()
        assert resp.status == 200
        assert "goal and progress confirmed" in data
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        os.environ.pop("CONTINUUM_DASHBOARD_TOKEN", None)


def test_dashboard_and_gateway_chunked_same_status(tmp_path: Path) -> None:
    """Both servers must agree on the chunked refusal code (#522 consistency)."""
    from continuum.gateway import GatewayServer, load_gateway_config

    # Gateway side
    gw_db = str(tmp_path / "gw.db")
    with SQLiteStorage(gw_db) as store:
        store.create_run(Run(run_id="run_1", goal="g"))
        store.append_event("run_1", EventType.RUN_STARTED, {"goal": "g"})
    cfg = load_gateway_config(tmp_path / "nope.json")
    gw = GatewayServer(lambda: SQLiteStorage(gw_db), "run_1", cfg, port=0)
    gw_thread = threading.Thread(target=gw.serve_forever, daemon=True)
    gw_thread.start()
    gw_addr = f"127.0.0.1:{gw.port}"
    # Dashboard side
    os.environ["CONTINUUM_DASHBOARD_TOKEN"] = "op-secret"
    dash_db = str(tmp_path / "dash2.db")
    with SQLiteStorage(dash_db) as store:
        store.create_run(Run(run_id="run_1", goal="g"))
        store.append_event("run_1", EventType.RUN_STARTED, {"goal": "g"})
    dash = make_dashboard_server(SQLiteStorage(dash_db), port=0)
    dash_thread = threading.Thread(target=dash.serve_forever, daemon=True)
    dash_thread.start()
    dash_addr = f"127.0.0.1:{dash.server_address[1]}"
    try:
        gw_raw = (
            b"POST /v1/invoices HTTP/1.1\r\n"
            b"Host: api.example.com\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"Content-Type: application/json\r\n"
            b"Connection: close\r\n\r\n"
            b"5\r\nhello\r\n0\r\n\r\n"
        )
        dash_raw = (
            b"POST /action/confirm HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"Content-Type: application/x-www-form-urlencoded\r\n"
            b"Connection: close\r\n\r\n"
            b"5\r\nhello\r\n0\r\n\r\n"
        )
        import socket

        def raw_status(addr: str, raw: bytes) -> int:
            host, port = addr.split(":")
            sock = socket.create_connection((host, int(port)), timeout=10)
            sock.sendall(raw)
            sock.settimeout(5)
            data = b""
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    data += chunk
            except OSError:
                pass
            finally:
                with contextlib.suppress(OSError):
                    sock.close()
            if not data:
                return 0
            header = data.split(b"\r\n")[0].decode(errors="ignore")
            try:
                return int(header.split()[1])
            except Exception:
                return 0

        gw_status = raw_status(gw_addr, gw_raw)
        dash_status = raw_status(dash_addr, dash_raw)
        assert gw_status == dash_status == 400
    finally:
        gw.shutdown()
        dash.shutdown()
        dash.server_close()
        gw_thread.join(timeout=5)
        dash_thread.join(timeout=5)
        os.environ.pop("CONTINUUM_DASHBOARD_TOKEN", None)
