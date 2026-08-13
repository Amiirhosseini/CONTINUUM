# MCP server: status, verification, and open questions

**Crash recovery at startup is fixed and tested.** A server process killed with
`SIGKILL` leaves orphaned `<db>-wal` / `<db>-shm` sidecars that previously made
the next launch fail with `sqlite3.OperationalError: disk I/O error`. The server
now opens its store through `_open_server_storage`, which on that error removes
the orphaned sidecars and retries the open exactly once, re-raising when there is
nothing to clear. Two regression tests in `tests/test_mcp_server.py` cover the
recovery and the re-raise. Recorded in CHANGELOG.md under Fixed.

**The server is verified usable through Claude Code.** Registered as an MCP
server, it reports `✔ Connected`, exposes all nine tools with the correct
read-only/mutating split, and the full `continuum_record_progress` to
`continuum_checkpoint` to `continuum_intercept_action` to
`continuum_complete_action` to `continuum_resume` cycle returns correct,
durable JSON. Authorization denies by default. That claim is proven end to end
over the real stdio protocol, and the unit suite (675 passed, 4 skipped) covers
every tool.
