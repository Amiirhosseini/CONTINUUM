"""Allows ``python -m continuum.cli`` alongside the installed ``continuum`` script.

Executed in a child interpreter by the subprocess tests, so coverage cannot see
it; the behaviour it enables is asserted there instead.
"""

from continuum.cli.main import main

if __name__ == "__main__":  # pragma: no cover - measured via subprocess
    raise SystemExit(main())
