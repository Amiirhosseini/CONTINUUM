"""Shared helpers for driving MCP tools in tests."""

from __future__ import annotations

from typing import Any


class _ClientInfo:
    def __init__(self, name: str) -> None:
        self.name = name
        self.version = "test"


class _Params:
    def __init__(self, name: str) -> None:
        self.client_info = _ClientInfo(name)


class _Session:
    def __init__(self, name: str) -> None:
        self.client_params = _Params(name)


class FakeContext:
    """Stands in for an MCP request context with a declared client identity.

    Mirrors the real shape the transport injects — ``session.client_params
    .client_info.name`` — which is read from the initialize handshake and
    cannot be set by a tool argument.
    """

    def __init__(self, name: str | None) -> None:
        self.session = _Session(name) if name is not None else None


def fake_context(name: str | None) -> Any:
    return FakeContext(name)
