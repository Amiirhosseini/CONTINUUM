# Project status

**As of commit `d32f7a2` — 2026-08-10.**

A factual snapshot for whoever picks this up next, human or otherwise, with no
memory of how any of it was found. It records what is verified, what is
believed, and what is neither.

---

## Verified

607 tests pass. CI is green on Python 3.11, 3.12 and 3.13, plus lint
(`ruff`) and strict type-check (`mypy`) — confirmed by run
[31355087372](https://github.com/Cyrax321/CONTINUUM/actions/runs/31355087372).
Everything below has tests behind it; several of the safety-critical paths have
also been checked by deliberately breaking them and confirming the suite
notices.

### Core

| Component | Module | Notes |
|:--|:--|:--|
| Event log | `events.py` | Append-only, hash-chained, per-run sequencing. `verify()` reports `trusted_through` so a partially tampered run can still be recovered up to its last good event. |
| State projection | `state/semantic.py` | Pure fold over an event prefix. Reproducible and prefix-closed. |
| Storage | `storage/sqlite.py` | WAL, `synchronous=FULL`, `IMMEDIATE` write transactions, `UNIQUE(run_id, sequence)`. Schema **v2**. |
| Checkpoints | `checkpoint/` | Policy-driven (manual, interval, event, semantic, context-pressure, hybrid). Restore replays events recorded after the checkpoint. |
| Validation | `state/validator.py` | Checks state against the current environment. Staleness propagates `dependency -> evidence -> finding -> decision`. |
| Action ledger | `actions/` | Idempotent claim/complete. Raises `UnknownSideEffect` rather than guessing when an outcome is unknown. |
| Recovery engine | `recovery/` | Reduces validation, ledger and checkpoint signals to one `RecoveryMode`. Takes the **maximum** on a severity ordering, so the most cautious signal wins regardless of evaluation order. |

### Interfaces

- **CLI** (`cli/`) — 14 commands, stdlib `argparse` only. Exit codes are a
  safety contract: only a verified-safe run exits `0`, so
  `continuum resume "$RUN" && ./start-agent.sh` cannot launch onto stale state.
  Colour is TTY-aware and respects `NO_COLOR`; piped output is byte-identical
  to uncoloured output.
- **`GenericAgentAdapter`** (`adapters/generic.py`) — in-process Python facade.
- **MCP server** (`mcp/server.py`) — 9 tools over stdio.

### MCP two-phase action interception

A Python callable cannot cross the MCP boundary, so the server cannot execute a
side effect on the caller's behalf. The protocol is:

1. `continuum_intercept_action` — claims the ledger entry, answers *may I?*
2. the caller performs the effect
3. `continuum_complete_action` — records the outcome

Between 1 and 3 the ledger holds a `STARTED` record. A caller that crashes or
never reports back leaves the action uncertain, and recovery refuses to resume
until it is reconciled. **This is intended.** An unreported effect is
indistinguishable from a completed one, and surfacing that is the ledger's
entire purpose.

---

## The self-certification fix (`9738b9e`)

### What the exploit was

An agent reaching the MCP server could fabricate progress and have CONTINUUM
confirm it was safe to resume:

```
record_progress(run_id='r', completed=9999, total=10000, goal=...)
checkpoint(run_id='r')
resume(run_id='r')

before:  mode=resume         safe=True
after:   mode=request_human  safe=False
```

### Why it happened

The projector hardcoded `Origin.DETERMINISTIC` for every component it folded.
That was true of the *fold* and false of the *claim* — faithfully folding a
fabricated event yields a faithful projection of a lie. `Origin` and
`Provenance` already existed, but neither the validator nor the recovery engine
consulted them, and `Goal`/`Progress` — the two fields the exploit falsifies —
carried no provenance at all.

### What closed it

- `Event.source` records who asserted a fact, captured at write time and
  included in `content()` so it is **signed**. A trust marker outside the digest
  could be edited without breaking verification.
- The projector propagates `event.source` instead of hardcoding. `Goal` and
  `Progress` now carry provenance.
- The validator marks self-certified components `REQUIRES_REVIEW`.
- Everything written through MCP is tagged `Origin.EXTERNAL_AGENT`.

Progress is cumulative, so the weakest contributor wins: a trusted event
appended after an agent's self-report does not launder the running total.

This required a **strict schema migration, v1 to v2, with no compatibility
branch**. Pre-existing event chains no longer verify. The database was reset as
part of the change.

Commit: `9738b9e`.

### What it does *not* fix

Provenance stops an agent certifying its own state. It does **not** stop an
unauthorized caller invoking mutating tools in the first place — that is the
authorization layer below.

---

## The MCP authorization layer (`d9365c8`)

Any client that could reach the server could call any tool. Several agents have
been configured against this project's database simultaneously — Kilo, Gemini
CLI and Claude Code all pointed at the same `continuum.db` — so any of them
could overwrite another's progress, checkpoint over its state, or claim its
actions.

Mutating tools now require the caller to appear on an allowlist. The caller is
identified by `client_info.name` from the initialize handshake, which the
transport injects server-side; a caller cannot elevate itself by passing a
forged `clientInfo` in tool arguments (verified against the live stdio
transport and covered by test).

**Deny by default.** An unlisted caller is not one we have decided to trust; it
is one nobody has made a decision about. An unconfigured server is therefore
read-only. This matches the validator's stance elsewhere: uncertainty degrades
rather than resolving in its own favour.

Policy resolves in four tiers, each replacing rather than merging the ones
below, so `AuthorizationPolicy.source` always names where a grant came from:

1. explicit `policy=` argument
2. `CONTINUUM_MCP_MUTATING_CLIENTS`, or its alias `CONTINUUM_MCP_ALLOW`
3. `.continuum/mcp-policy.json`
4. deny

A malformed policy file raises rather than falling back — a file that exists is
a statement of intent, and ignoring a typo in it would either baffle the owner
or quietly widen access.

**Read-only tools are not gated.** `validate`, `resume` and `list_actions`
cannot alter a run, and their value is that anyone can ask "is this safe to
continue?" without first being granted permission. Gating them would also leave
an unlisted caller unable to discover why its writes are failing. The
information they disclose is already readable by anyone holding the database
file. The split is driven by the `read_only_hint` annotation each tool already
declared, so the two cannot drift apart.

### What it does *not* do

`clientInfo` is asserted by the client at handshake and never verified. A caller
that wants to be seen as `claude-code` simply says so. **This is authorization
by declared identity, not authentication.**

It keeps honestly-named coexisting agents out of each other's runs. It does not
defend against a deliberately impersonating or malicious local process — which
in any case has direct filesystem access to the database and does not need the
MCP server at all.

Also out of scope: rate limiting, audit of failed attempts beyond the error
response, and scoping callers to particular runs.

### Naming (`d32f7a2`)

`CONTINUUM_MCP_MUTATING_CLIENTS` is accepted as an alias for
`CONTINUUM_MCP_ALLOW`, occupying the same precedence position rather than adding
a config source. If both are set the longer name wins, since it states what is
being allowed; `policy.source` reports which was used. The name is preserved
from the closed PR #3 below.

---

## PR #3: an authorization attempt that failed open

Worth reading before touching this code.
[PR #3](https://github.com/Cyrax321/CONTINUUM/pull/3) was an independently
developed attempt at the same fix, with the right shape — handshake identity,
enforcement at the MCP boundary, read-only tools left callable. It was reviewed
and **closed without merging** because its guard authorized the caller on two
failure paths:

```python
if mcp_context is None:
    return                    # allows
try:
    params = mcp_context.session.client_params
except ValueError:
    return                    # allows
```

The `ValueError` path is reachable: `Context.request_context` raises exactly
`ValueError("Context is not available outside of a request")` when `.session` is
touched outside a live request. Replicating the guard verbatim and invoking it
the way the test suite invokes tools produced
`{"authorized": true, "why": "ValueError -> allowed"}`.

The instructive part is not the missing `raise`. The PR modified
`tests/test_mcp_server.py` but added no test of the gate itself, so the fail-open
produced a green checkmark — and its `Fixes #1` footer would have auto-closed
the issue on merge. Passing tests, a closed issue, and an open hole is a worse
outcome than no fix at all.

Two things were kept from it: the `CONTINUUM_MCP_MUTATING_CLIENTS` name, and the
observation that raising `ToolError` directly is a defensible alternative to the
`PermissionError` subclass used here.

---

## Open items

| Issue | Summary | Priority |
|:--|:--|:--|
| [#1](https://github.com/Cyrax321/CONTINUUM/issues/1) | **MCP caller authentication.** Narrowed by `d9365c8`: authorization for mutating tools now exists and denies by default. What remains is authentication — `clientInfo` is client-asserted and unverified, so a deliberately impersonating local process is unaffected. Would need a shared secret, per-client token, or transport-level identity. | Medium |
| [#2](https://github.com/Cyrax321/CONTINUUM/issues/2) | **CI Node deprecation.** `actions/checkout@v4`, `actions/setup-python@v5`, `codecov/codecov-action@v4` are being forced onto Node 24. Works today; hard failure once the grace period ends. `release.yml` likely has the same pins and was not checked. | Low |

### Not built

Phases 12–14 of the original plan: benchmark suite (CONTINUUM-Bench), cloud API,
dashboard. `adapters/` contains only `base.py` and `generic.py` — the OpenAI and
LangGraph adapters do not exist. **No benchmark numbers have been measured**, and
`continuum benchmark` exits `4` saying so.

---

## Third-party MCP client testing

Both clients connected to the server and successfully invoked tools. **Neither
completed a full checkpoint → resume cycle.**

| Client | Connected | Tools called | Outcome |
|:--|:--|:--|:--|
| Gemini CLI | yes, health-checked `✓ Connected` | `record_progress` ×4 | First call registered a run and wrote events. A later call failed on the `pending`-recomputation bug (fixed in `9738b9e`). |
| Kilo Code | yes, via its own `kilo.jsonc` | `record_progress` | Wrote a run row and a `RUN_STARTED` event, then stopped. |

Neither called `continuum_checkpoint` or `continuum_resume` at any point, even
before hitting errors. Whether that reflects tool descriptions that do not
motivate use, or simply an incomplete task, is **not established**. Worth
re-running now the blocking bug is fixed.

Note: the evidence for the Kilo run was in a database that has since been reset
by the v2 migration. The Gemini session transcript persists under
`~/.gemini/tmp/`, but that is outside the repository and not durable.

---

## Unresolved

`demo_report.md` (an untracked artifact from the third-party testing above)
changed from 4,997 bytes with five sections to 746 bytes with one, between two
examinations during a single working session. Nothing in this repository
accounts for it.

At the time, `claude` and `gemini` CLI processes were running on other TTYs,
and two `kilo serve` processes had been running all day. **Concurrent agent
sessions are the most plausible explanation, but this was inferred from process
listings and timestamps — it was never confirmed.** It is recorded here as an
open question rather than a closed one.

A related, confirmed observation: files in this repository were modified during
this work by processes other than the session doing the work — including an
`adapters/` package and a `recovery/engine.py` branch that appeared
mid-session. If state seems to change without explanation, check for other
agent processes before assuming a bug.

---

## Untracked files, deliberately excluded

- `.mcp.json` — Claude Code registration; hard-codes machine-specific absolute
  paths.
- `demo_report.md` — artifact from third-party client testing.
- `kilo.jsonc` — Kilo's own MCP config, written by Kilo.
