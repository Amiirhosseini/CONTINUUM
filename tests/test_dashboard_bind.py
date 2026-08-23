"""Dashboard bind hardening (issue #270).

The dashboard renders recovery contracts with goals and side-effect details;
it must default to loopback like every other CONTINUUM server. Operators opt
into exposure explicitly via --host.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

import pytest

from continuum.dashboard.app import make_dashboard_server
from continuum.storage import SQLiteStorage


@pytest.fixture
def db(tmp_path: Path) -> str:
    return str(tmp_path / "bind.db")


def test_default_bind_is_loopback(db: str) -> None:
    server = make_dashboard_server(SQLiteStorage(db))
    host, port = server.server_address[:2]
    assert host == "127.0.0.1"
    assert isinstance(port, int) and port > 0
    server.server_close()


def test_explicit_zero_conf_host_is_honoured(db: str) -> None:
    server = make_dashboard_server(SQLiteStorage(db), host="0.0.0.0")
    assert server.server_address[0] in ("0.0.0.0", "")
    server.server_close()


def test_handler_serves_the_dashboard_over_a_real_socket(db: str) -> None:
    """End-to-end smoke through the constructed server: GET / renders."""
    import threading

    server = make_dashboard_server(SQLiteStorage(db), port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        _, port = server.server_address[:2]
        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5)
        body = resp.read().decode()
        assert resp.status == 200
        assert "CONTINUUM Dashboard" in body
    finally:
        server.shutdown()
        server.server_close()
