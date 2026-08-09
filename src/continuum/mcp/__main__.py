"""Allows ``python -m continuum.mcp`` alongside the ``continuum-mcp`` script."""

from continuum.mcp.server import main

if __name__ == "__main__":  # pragma: no cover - exercised via subprocess
    raise SystemExit(main())
