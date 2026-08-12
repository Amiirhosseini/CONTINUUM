# Project status

**As of 2026-08-12** (commit `d32f7a2` was the last tagged state; subsequent
entries added the framework adapters, Inspector CLI verification, and CI
Node 24 migration).

A factual snapshot for whoever picks this up next, human or otherwise, with no
memory of how any of it was found. It records what is verified, what is
believed, and what is neither.

---

## Verified

653 tests pass, 4 skip, run from a clean `HEAD` (0e2a43a) on Python 3.13 with
`mcp 2.0.0` installed. The MCP server tests are no longer excluded: they load
and pass against `mcp>=2.0` (the version pinned in `pyproject.toml`). An
earlier note recorded them as failing to load; that incompatibility is gone
with the newer SDK. CI was green on Python 3.11, 3.12 and 3.13, plus lint
(`ruff`) and strict type-check (`mypy`) — confirmed
by run
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
- **`LangGraphAgentAdapter`** (`adapters/langgraph.py`) — LangGraph
  integration, optional `langgraph` dependency.
- **`OpenAIAgentAdapter`** (`adapters/openai.py`) — OpenAI Agents SDK
  integration, optional `openai-agents` dependency.
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

### Code audit findings (2026-08-12)

A module-by-module audit filed seven issues, each reproduced against clean
`HEAD` (455e307) and filed with the `bug_report` template:

| Issue | Summary | Priority |
|:--|:--|:--|
| [#15](https://github.com/Cyrax321/CONTINUUM/issues/15) | **Over-total progress is a partial write.** `record_progress`/event writers commit a `TASK_UPDATED` whose `completed + pending + failed > total`; the log then passes `verify_events` but every projection, checkpoint, resume and validate raises a raw pydantic `ValidationError`, permanently, with no rollback. | High |
| [#20](https://github.com/Cyrax321/CONTINUUM/issues/20) | **Read-only `list_actions` writes.** Annotated `read_only` (and therefore ungated), `continuum_list_actions` calls `ensure_run`, backfilling `RUN_STARTED` into a bare run's log. Contradicts the read-only split guarantee. | High |
| [#16](https://github.com/Cyrax321/CONTINUUM/issues/16) | **STALE STATE section droppable.** `build_recovery_context` protects sections by sorted index, not identity: with `next_action` present, the STALE STATE section falls outside the `protected = 3` window and is dropped under a tight budget despite the never-dropped promise. | High |
| [#21](https://github.com/Cyrax321/CONTINUUM/issues/21) | **OpenAI adapter cannot auto-provision runs.** `_ensure_run_exists` reads via `get_run` which raises rather than returning `None`, so its `create_run` branch is dead code and `on_agent_start` raises `RunNotFound` for any fresh run. | Medium |
| [#17](https://github.com/Cyrax321/CONTINUUM/issues/17) | **Older-schema DB accepted silently.** A pre-v2 file opens without `SchemaVersionError` (only newer versions are rejected), `read_events` returns `[]` for a populated run, and the first write fails with a raw sqlite `OperationalError`. No migration path exists. | Medium |
| [#19](https://github.com/Cyrax321/CONTINUUM/issues/19) | **`resume --repair` is a no-op.** Help and docstrings claim `--repair` records the repair plan (and is one of only three mutating commands); in practice it only suppresses a stderr hint, writing nothing. | Medium |
| [#18](https://github.com/Cyrax321/CONTINUUM/issues/18) | **`events` breaks the exit-code contract.** `continuum events $MISSING` exits 0 with "No events.", while every other run-scoped command exits 2; `events` is absent from the enforcing parametrised test. Tagged `good first issue`. | Medium |

## The CI Node 24 migration (2026-08-12)

### What the issue was

GitHub-hosted actions running on Node 20 were being migrated to Node 24. Actions
whose `action.yml` declares `using: node20` emit deprecation warnings and will
hard-fail once GitHub ends its grace period. Three of the actions pinned in this
project's workflows ran on Node 20:

| Action | Pin | `using` |
|:--|:--|:--|
| `actions/checkout` | v4 | `node20` |
| `actions/setup-python` | v5 | `node20` |
| `codecov/codecov-action` | v4 | `node20` |

`release.yml` had the same `checkout`/`setup-python` pins plus `upload-artifact`
and `download-artifact` at v4 (also `node20`), and `softprops/action-gh-release@v2`
(`node20`). `deploy-pages.yml` had `checkout@v4` and `deploy-pages@v4`
(`node20`).

### What closed it

Each action was bumped to the latest stable major version, which publishes
`using: node24` in its `action.yml`:

| Action | Old pin | New pin |
|:--|:--|:--|
| `actions/checkout` | v4 | **v7.0.1** |
| `actions/setup-python` | v5 | **v7.0.0** |
| `codecov/codecov-action` | v4 | **v7.0.0** |
| `actions/upload-artifact` | v4 | **v7.0.1** |
| `actions/download-artifact` | v4 | **v8.0.1** |
| `actions/configure-pages` | v5 | **v6.0.0** |
| `actions/deploy-pages` | v4 | **v5.0.0** |
| `softprops/action-gh-release` | v2 | **v3.0.2** |

`actions/upload-pages-artifact@v3` was left at v3: it uses `runs: using: composite`,
which is not subject to the Node deprecation (composite actions run as workflow
steps, not in a Node runtime). `pypa/gh-action-pypi-publish@release/v1` was also
left unchanged: it is a composite action.

### How verified

YAML syntax validated with `yaml.safe_load_all()` on all three workflow files.
The new versions were confirmed by fetching each action's latest stable release
tag via the GitHub API and reading its `action.yml` `runs.using` field to verify
`node24` (or `composite` for `upload-pages-artifact`). Confirmed by CI run
[31534363260](https://github.com/Cyrax321/CONTINUUM/actions/runs/31534363260)
— all four jobs green: ruff lint, ruff format, mypy strict, and tests on
Python 3.11 / 3.12 / 3.13.

### Not done

No action version was bumped to a prerelease, draft, or non-semver tag. All
selected versions are the highest stable semver release for each action as of
2026-08-12.

---

## Not built

Phases 12–14 of the original plan: benchmark suite (CONTINUUM-Bench), cloud API,
dashboard. **No benchmark numbers have been measured**, and `continuum benchmark`
exits `4` saying so.

### Framework adapters (Phase 11)

`adapters/` now contains `base.py`, `generic.py`, `langgraph.py`, and
`openai.py`. Both are optional dependencies — `langgraph` and `openai-agents`
are not pulled in by `pip install continuum-agent`; install via
`pip install continuum-agent[langgraph]` or `[openai]`. Each was written after
checking the target framework's actual API surface (ToolContext/RunHooks for
OpenAI Agents SDK; StateGraph/TypedDict for LangGraph), not an assumed shape.
Tests cover behavior without the SDK installed (mocked), with it installed
(integration class, skip-guarded), and the established `AgentAdapter`
contract.

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

## MCP Inspector CLI verification (2026-08-12)

The MCP server was tested end-to-end using `@modelcontextprotocol/inspector`
v2.1.0 in `--cli` mode, which drives the real stdio protocol boundary — the
inspector spawns the server as a subprocess, performs the initialize handshake
over JSON-RPC 2.0 over stdio, and pipes tool calls through the transport. This
is **not** an in-process pytest call.

```
npx @modelcontextprotocol/inspector --cli --config mcp-config.json \
  --server continuum --method tools/list --format json
```

All 9 tools were returned (`tools/list`): `continuum_record_progress`,
`continuum_checkpoint`, `continuum_validate`, `continuum_resume`,
`continuum_intercept_action`, `continuum_complete_action`,
`continuum_fail_action`, `continuum_reconcile_action`,
`continuum_list_actions`. The read-only/mutating annotation split was as
declared (3 read-only, 6 mutating).

Test database: `.continuum/inspector-test.db`, separate from any prior history,
created fresh and deleted afterward. Authorization was granted via config-file
env (`CONTINUUM_MCP_MUTATING_CLIENTS=inspector-cli`); the caller name observed
in the handshake was `inspector-cli`, injected by the transport server-side.

Each sequence below used a new inspector invocation per call — the server
process was killed between calls (the inspector spawns a fresh subprocess per
`--method` invocation). Crashes are therefore real process deaths, not simulated
exceptions.

### Sequence A — clean crash, MCP-written state

```
record_progress(run_id='run_a_001', completed=50, total=200)
record_progress(run_id='run_a_001', completed=100, total=200)
checkpoint(run_id='run_a_001')
                        ← server process ends here
resume(run_id='run_a_001')   ← new server process, same db
```

Result (`continuum_resume` JSON):

```json
{
  "mode": "request_human",
  "safe": false,
  "next_allowed_action": "human_review:goal",
  "rationale": ["at least one repair needs a person"],
  "repairs": [
    {"action": "human_review:goal", "kind": "human_review",
     "reason": "v1, asserted by external_agent", "requires_human": true},
    {"action": "human_review:progress", "kind": "human_review",
     "reason": "100 completed, self-reported by external_agent and not independently verified",
     "requires_human": true}
  ],
  "uncertain_actions": [],
  "progress": {"completed": 100, "pending": 100, "failed": 0, "total": 200}
}
```

MCP-written state (`Origin.EXTERNAL_AGENT`) is correctly not trusted: goal and
progress are `REQUIRES_REVIEW`, mode is `request_human`. No uncertain actions —
the crash happened *after* checkpoint, not mid-action.

### Sequence B — crash between intercept and complete

```
record_progress(run_id='run_b_001', completed=0, total=100)
intercept_action(run_id='run_b_001', action_type='test.write_file', arguments={...})
                        ← server killed here; complete_action never called
resume(run_id='run_b_001')   ← new server process
list_actions(run_id='run_b_001')
```

`intercept_action` returned `proceed: true`, status `started` — the action was
claimed in the ledger. The resume JSON:

```json
{
  "mode": "request_human",
  "safe": false,
  "next_allowed_action": "reconcile_action:action_ee2437c3ddb0ed69fa8d5766c9e051bd",
  "rationale": [
    "1 external side effect(s) have unknown outcomes",
    "at least one repair needs a person"
  ],
  "repairs": [
    {"action": "reconcile_action:action_ee2437c3ddb0ed69fa8d5766c9e051bd",
     "kind": "reconcile_action",
     "reason": "test.write_file was interrupted; the side effect may or may not have occurred",
     "requires_human": false},
    {"action": "human_review:goal", "kind": "human_review",
     "reason": "v1, asserted by external_agent", "requires_human": true},
    {"action": "human_review:progress", "kind": "human_review",
     "reason": "0 completed, self-reported by external_agent and not independently verified",
     "requires_human": true}
  ],
  "uncertain_actions": [
    {"action_id": "action_ee2437c3ddb0ed69fa8d5766c9e051bd",
     "action_type": "test.write_file", "status": "started"}
  ],
  "progress": {"completed": 0, "pending": 100, "failed": 0, "total": 100}
}
```

`list_actions` confirmed the ledger state:

```json
{
  "actions": [
    {"action_id": "action_ee2437c3ddb0ed69fa8d5766c9e051bd",
     "action_type": "test.write_file",
     "external_id": null, "side_effect_uncertain": false,
     "status": "started"}
  ],
  "unresolved": 1
}
```

The action was not silently completed, not retried, not dropped. It stayed
`started`, surfaced in `uncertain_actions`, and the contract named
`reconcile_action:<id>` as the next required step. `safe: false`.

### Sequence C — trusted-writer state, clean crash

State was created in-process via `GenericAgentAdapter` (not through MCP), with
150 `WORK_COMPLETED` events folded into the checkpoint. Origin:
`DETERMINISTIC` for all components. `source_sequence: 156`.

```
# state written in-process, checkpointed, then:
resume(run_id='run_c_001', env={dataset: v1})
```

Result:

```json
{
  "mode": "resume",
  "safe": true,
  "next_allowed_action": null,
  "repairs": [],
  "progress": {"completed": 150, "failed": 0, "pending": 50},
  "contract": {
    "recovery_status": "safe_to_resume",
    "verified": ["approval:apr_001", "external_dependency:dataset", "goal", "progress"],
    "invalidated": [],
    "required_actions": []
  }
}
```

Exit code: **0**. Trusted-writer state whose environment matches resumes cleanly.

### What this establishes

The self-certification fix (`9738b9e`) behaves correctly under a real external
MCP client hitting a real process boundary — not just in pytest:

- MCP-attested state cannot self-certify safety (Sequences A, B → `request_human`)
- A crash between `intercept_action` and `complete_action` leaves the action
  uncertain and blocks resume until reconciled (Sequence B)
- Trusted-writer state resumes cleanly when warranted (Sequence C → `resume`,
  exit 0) — ruling out the alternative explanation that the system simply never
  resumes

The MCP server's two-phase action interception, ledger uncertainty handling, and
authorization gating all functioned as documented when driven through the
actual stdio protocol by an external process.

### What this does NOT establish

This was still a **scripted** test. The building agent itself acted as the MCP
client, following an exact predetermined sequence. No independent LLM (Claude
Code, Gemini CLI, etc.) has yet chosen *on its own initiative* to call
`continuum_checkpoint` or `continuum_resume` without being told the exact steps.
Whether the tool descriptions actually motivate correct **autonomous** usage by
an LLM agent — calling checkpoint at the right moment, calling resume before
acting, respecting the response — remains **open**. This is the same question
flagged in the Third-party MCP client testing section above (neither Gemini nor
Kilo completed a cycle either), and it is unanswered by this test.

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

## Repository housekeeping

The commit history on `main` is dominated by website and logo iteration: roughly 50 of ~115 commits are site, favicon, or logo experiments, including one revert (`ea583ec`). This is cosmetic churn, not open code debt. Not tracked as a GitHub issue: rewriting history on a repository others may have forked is disruptive, and a public flame-on-commits is low value. If a clean history matters for the v0.1.0 presentation, squash or rewrite those commits before release; otherwise leave them.

---

## Untracked files, deliberately excluded

- `.mcp.json` — Claude Code registration; hard-codes machine-specific absolute
  paths.
- `demo_report.md` — artifact from third-party client testing.
- `kilo.jsonc` — Kilo's own MCP config, written by Kilo.
