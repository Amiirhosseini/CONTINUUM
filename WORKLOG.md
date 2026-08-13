# Worklog

A chronological record of what was done and why, for whoever picks this up
next. It complements `STATUS.md` (the state snapshot and verification record)
and `CHANGELOG.md` (user-facing changes). Where this document summarises a
session, `STATUS.md` carries the detail and the evidence.

## Session 1: v0.1.0 core and first release (2026-08-11)

Built CONTINUUM v0.1.0 from the plan in `project.md`.

- Phase 1 core: event log, deterministic semantic state fold, immutable state
  versioning, checkpoint diffing.
- Phase 2: SQLite transactional event store (WAL, `synchronous=FULL`,
  IMMEDIATE transactions, hash-chained append-only log), semantic checkpoint
  manager with adaptive persistence policies, invariant state validator.
- Interactive website and live fault simulator moved into `docs/`, GitHub
  Pages deploy workflow added.

First release commit: `ee9032b`.

Most of the 2026-08-11 history after that is website and logo iteration
(roughly 50 of ~115 commits at the time). One revert (`ea583ec`) undid a
stylesheet split. Noted in `STATUS.md` under Repository housekeeping.

## Session 2: CLI, action ledger, adapters (2026-08-11)

- Phase 8 CLI: 14 stdlib-argparse commands with TTY-aware colour, `NO_COLOR`
  support, and the exit-code contract (only a verified-safe run exits `0`).
- `feat(actions)`: idempotent action ledger with claim/complete, raising
  `UnknownSideEffect` rather than guessing an unknown outcome.
- `feat(adapters)`: generic `AgentAdapter` facade, then LangGraph and OpenAI
  Agents SDK adapters, written against each framework's actual API surface.
- `feat(examples)`: context compaction and model switch demos (Phase 9).

## Session 3: security and authorization (2026-08-11)

- `9738b9e` carried event provenance so agents cannot self-certify state:
  `Event.source` is captured at write time and signed; the projector propagates
  it; the validator marks self-certified components `REQUIRES_REVIEW`;
  MCP-written state is tagged `Origin.EXTERNAL_AGENT`. Required a strict v1 to
  v2 schema migration; the database was reset.
- `103b83c` gated mutating MCP tools behind a caller allowlist, deny by default.
  `CONTINUUM_MCP_MUTATING_CLIENTS` accepted as an alias for the older
  `CONTINUUM_MCP_ALLOW` name (`05770b4`).
- PR #3 (an independent attempt at the same authorization fix) was reviewed
  and closed without merging because it failed open on two paths. The
  `CONTINUUM_MCP_MUTATING_CLIENTS` name was kept from it. Full write-up in
  `STATUS.md`.

## Session 4: MCP Inspector verification (2026-08-12)

Verified the server end to end through `@modelcontextprotocol/inspector`
v2.1.0 in `--cli` mode, driving the real stdio protocol boundary. Three
sequences (clean crash, crash between intercept and complete, trusted-writer
state) confirmed the two-phase interception, uncertainty handling, and
authorization behave correctly under real process deaths. Scripted, not
autonomous. Detail and JSON in `STATUS.md`.

## Session 5: code audit and audit-driven fixes (2026-08-12)

A module-by-module audit filed seven issues and produced four fixes, each with
regression tests:

- `91aee41` rejects over-total progress before it is written (issue #15).
- `71c86b3` stops read-only `list_actions` from backfilling `RUN_STARTED`
  (issue #20).
- `e9c5f78` protects the never-dropped recovery-context sections by identity,
  not sorted position (issue #16).
- `1bcc933` makes `continuum events` honour the not-found exit code (issue
  #18).

CI was migrated to Node 24-compatible GitHub Actions (`d8f80dd`). Adapter
lint, format, and mypy issues were resolved (`6fb91a0` through `89307ff`).
`examples/` were made lint-clean and added to CI coverage (issue #8).
CONTRIBUTING clone URL, PyPI homepage, license copyright, and a publishing /
premium roadmap plan were fixed or added.

## Session 6: CONTINUUM-Bench (2026-08-12)

`feat: add CONTINUUM-Bench minimal recovery benchmark harness` (`0bebb61`):
`continuum benchmark` runs three scenarios across three strategies and prints
measured numbers. Phase 12 shipped in minimal form; the fuller suite, published
baselines, and dashboard remain a goal.

## Session 7: Claude Code MCP verification and orphaned-WAL fix (2026-08-13)

- Registered the server in Claude Code and drove it end to end from a real
  session. All 9 tools callable, authorization boundary intact, MCP-written
  state resumes as `request_human` / `safe: false`.
- Hit `Failed to connect`: a previously hard-killed server had left orphaned
  `<db>-wal` / `<db>-shm` sidecars, and the next open failed at
  `PRAGMA journal_mode=WAL` with `disk I/O error`.
- `8ef54c9` self-heals at startup: `_open_server_storage` clears orphaned
  sidecars and retries the open once, re-raising when there was nothing to
  remove. Two regression tests.
- `b8a055c` added `e2e-autonomy-test/`: a three-script harness to answer the
  still-open question of whether an unscripted LLM agent would use CONTINUUM
  correctly on its own.

## Session 8: the issue #6 e2e series (2026-08-13)

Three full runs against real Claude Code sessions, each hard-killed mid-batch
and resumed in a brand-new session. All scored 7/7 on the mechanics checks and
demonstrated real autonomy: agents used `record_progress`, routed sends through
intercept/write/complete, called `resume` before acting, surfaced the
`request_human` verdict, and refused to re-send verified-sent invoices.

The runs exposed a dedup defect: `continuum_intercept_action` hashed the
caller's raw arguments, so relative vs absolute path formatting produced
different idempotency keys and the resumed session was told `proceed: true`
for already-sent invoices. Fixed in `1fc97cf` by adding a stable `key`
argument (e.g. `invoice:INV-001`) that makes two attempts the same action
regardless of argument shape. Regression test mirrors the exact failure.

Also recorded: ledger pollution from the `fail_action(certain=true)`
workaround (gone with the fix), and an open observation that
`continuum_resume` reported `checkpoint_version: 0` despite session 1 taking a
checkpoint. Full detail in `STATUS.md` under "The issue #6 e2e series".

## Session 9: ledger performance profiling (2026-08-13)

Measured the suspect lag seen when resuming after 4-5 actions. Findings:

- Ledger replay is O(n) per call, O(n^2) over a run: 10 actions at 1.5 ms per
  call, 200 actions at 23.4 ms per call (ratio 100 to 200: 2.06x).
- MCP server-side calls are fast at e2e scale: `list_actions` 4.7 ms, `resume`
  0.7 ms at 5 actions. Event append including fsync about 0.15 ms.
- Conclusion: the perceived lag is dominated by LLM round trips per tool call
  (seconds-scale), not the database. Fewer tool calls is the lever, and the
  dedup fix is the change that removes the spurious call cycle. The O(n^2)
  replay is real but negligible below hundreds of actions; a replay cache is
  deferred until a run grows that large.

## Session 10: defensive dedup hardening (2026-08-13)

Re-read the three e2e transcripts and found the real drift was argument field
renames (`target` / `outbox_file` / `outfile` / `file`), action type drift in
one run (`send_invoice` vs `send-invoice-email`), and `external_id` shape
drift. The only stable identity was the resource token (`INV-001`), surviving
as scalar value, path basename, and external id stem. The stable-key fix could
not help when the caller supplied no key or renamed fields.

Added two defensive layers:

1. `arguments_hash` / `idempotency_key` now canonically normalize path-like
   arguments (lexical `normpath` plus `~` expansion; URLs untouched) before
   hashing.
2. `ActionLedger.claim()` gains a token-based identity fallback for the
   no-explicit-key case: shared identity tokens (scalar values, path
   basenames/stems, external ids; weak tokens and the `continuum_run_id`
   plumbing token excluded) recognize a unique same-type match. Completed match
   returns `fresh=False` with the stored result and real recorded key;
   interrupted match surfaces as uncertain; ambiguity falls through.

Caught during testing: the fallback initially deduplicated distinct tool calls
because `continuum_run_id` (a strong token) was present in every claim's
arguments; the plumbing exclusion fixed it and a regression test pins it.

Verification: 700 tests pass, ruff clean, mypy clean on changed files.

## Open items carried forward

- Issue #1: MCP authentication (authorization exists; `clientInfo` remains
  client-asserted).
- Issue #17: older-schema databases accepted silently; no migration path.
- Issue #19: `resume --repair` is a no-op.
- Orphaned `demo_report.md` size change and concurrent-agent edits (inferred,
  never confirmed).
- `checkpoint_version: 0` on resume despite a session-1 checkpoint.
- Stale editable metadata in `pip show continuum-agent` (cosmetic).
- Re-running the e2e kit after the dedup fix to confirm the positive path
  (`proceed: false` on resume without agent workaround) before closing issue
  #6.