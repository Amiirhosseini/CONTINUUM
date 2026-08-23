<p align="center">
  <img src="docs/assets/readme-img.png" alt="CONTINUUM Banner" width="100%" />
</p>

<p align="center">
  <strong>CONTINUUM: Verifiable semantic recovery for long-running AI agents.</strong>
  Semantic checkpoints (not conversation dumps), an idempotent action ledger
  that refuses duplicate side effects, and a hash-chained tamper-evident event
  log, all exposed as a deny-by-default MCP server. Framework-agnostic,
  Python 3.11+.
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue?style=flat-square" alt="License" /></a>
  <a href="https://pydantic.dev"><img src="https://img.shields.io/badge/pydantic-v2-E92063?style=flat-square&logo=pydantic&logoColor=white" alt="Pydantic v2" /></a>
  <a href="https://continuum-nu-six.vercel.app/"><img src="https://img.shields.io/badge/website-live_demo-E06D53?style=flat-square" alt="Website Demo" /></a>
  <a href="https://github.com/Cyrax321/CONTINUUM/actions/workflows/ci.yml"><img src="https://github.com/Cyrax321/CONTINUUM/actions/workflows/ci.yml/badge.svg" alt="CI status" /></a>
  <a href="https://app.codecov.io/gh/Cyrax321/CONTINUUM"><img src="https://img.shields.io/codecov/c/github/Cyrax321/CONTINUUM?style=flat-square&logo=codecov" alt="Coverage" /></a>
</p>

<p align="center">
  <a href="https://continuum-nu-six.vercel.app/"><strong>Visit the CONTINUUM website</strong></a>
</p>

---

## Contents

[Why](#why) · [Quick Start](#quick-start) · [How it works](#how-it-works) · [Features](#features) · [Security Extension](#security-extension) · [Empirical Verification](#empirical-verification) · [MCP Integration](#mcp-integration) · [Framework Integration](#framework-integration) · [Core Concepts](#core-concepts) · [Architecture](#architecture) · [API and CLI](#api-and-cli) · [Roadmap](#roadmap) · [What CONTINUUM Is Not](#what-continuum-is-not) · [Related work](#related-work) · [Status and limitations](#status-and-limitations) · [Contributing](#contributing) · [License](#license)

---

## Why

Modern AI agents run long tasks (hundreds of LLM calls, tool invocations, file and database writes). When they crash, the usual response is to replay everything from scratch, which duplicates work, duplicates side effects, wastes tokens, and loses decisions.

CONTINUUM asks a narrower, harder question: can an agent resume from a compact semantic representation of its task state while independently verifying that state is still valid in the current environment? It is not a generic agent framework, a memory system, or a workflow engine. Its differentiator is three-part:

- **Semantic checkpoints**: a compact, versioned representation of what the agent needs to continue, not a conversation dump.
- **Independent environment revalidation**: every checkpoint component is verified against the current environment before resume, with staleness propagating through the dependency graph.
- **Provenance-aware state**: every fact traces to its origin, so agent-reported progress is never self-certifying.

## Quick Start

Not published to PyPI yet. Install from a clone. One clone is enough to get the library, CLI, MCP server, and every adapter ready for contribution.

### Prerequisites

| Requirement | Version / Notes |
|:--|:--|
| Python | **3.11+** (3.12 recommended for development, CI tests 3.11 / 3.12 / 3.13) |
| git | any recent version |
| uv **or** pip | `uv` is recommended (faster, lockfile-aware). `pip` works with a manual venv. |
| SQLite | bundled with Python, no extra install (WAL mode is used) |
| Optional: Docker | only for `ContainerAdapter` and Postgres integration tests |
| Optional: PostgreSQL 16 | only for `continuum-agent[postgres]` (`CONTINUUM_TEST_POSTGRES_DSN`) |
| Optional: Node.js | only if you re-build `docs/` frontend |

### 1. Clone

```bash
git clone https://github.com/Cyrax321/CONTINUUM.git
cd CONTINUUM
```

### 2. Create a virtual environment

With **uv** (recommended):

```bash
uv venv                          # creates .venv with Python 3.11+
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows PowerShell
```

With plain **pip/venv** (no uv):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 3. Install — pick your level

The core library has **one** runtime dependency (`pydantic>=2.7`). Everything else is an optional extra (see `pyproject.toml:30` and `pyproject.toml:32-72`).

**For contributors (recommended, installs everything you need to run tests, lint, and type-check):**

```bash
uv pip install -e ".[dev]"       # library + CLI + all test/tooling
```

This single command is enough to contribute. It pulls `mcp`, `langgraph`, `openai-agents`, `langchain`, and `cryptography` so `mypy` can type-check the adapter modules and `pytest` can exercise them. To verify, run:

```bash
continuum --help
continuum-mcp --help             # MCP server entrypoint (via dev extra's mcp)
pytest -q                        # 1252 passed (skipped varies by env, no extra services needed)
```

**Minimal install (just the library + CLI, zero adapter overhead):**

```bash
uv pip install -e .              # pydantic only
continuum --help                 # works, SQLite-backed
```

**Add only what you need (composable extras):**

```bash
uv pip install -e ".[mcp]"       # MCP server (11 stdio tools) — requires mcp>=2.0
uv pip install -e ".[otel]"      # OpenTelemetry bridge — opentelemetry-api>=1.20
uv pip install -e ".[langgraph]" # LangGraph adapter
uv pip install -e ".[openai]"    # OpenAI Agents SDK adapter (also pulls mcp transitively)
uv pip install -e ".[langchain]" # LangChain adapter
uv pip install -e ".[attest]"    # Ed25519 attestation (continuum attest)
uv pip install -e ".[postgres]"  # PostgreSQL backend — psycopg>=3.2
uv pip install -e ".[dev,postgres]" # full dev + live Postgres contract tests
```

Combine freely: `uv pip install -e ".[dev,postgres]"` (`[dev]` already includes `mcp`, `langgraph`, `langchain`, `openai-agents`, and `cryptography`).

> **pip fallback:** replace `uv pip install` with `pip install` in every command above if you are not using `uv`. `uv.lock` pins the resolved versions (`uv.lock:1`) but is optional with pip.

### 4. What gets installed (packages)

| Package | Where declared | Purpose | Required? |
|:--|:--|:--|:--|
| `pydantic>=2.7` | `pyproject.toml:30` (core `dependencies`) | Immutable models, hash-chained events | **Yes, always** |
| `mcp>=2.0` | `pyproject.toml:53` (`[mcp]`), also in `[dev]` | MCP server (`continuum-mcp`) stdio transport | Only for MCP server (also pulled transitively by `openai-agents`) |
| `opentelemetry-api>=1.20` | `pyproject.toml:55` (`[otel]`) | Span-processor bridge (`continuum.otel`) | Only for OTel directly; may appear transitively via `mcp`/`openai-agents` |
| `langgraph>=0.2` | `pyproject.toml:58` (`[langgraph]`) | LangGraph adapter | Only for LangGraph (also pulled transitively by `langchain`) |
| `openai-agents>=0.2` | `pyproject.toml:61` (`[openai]`) | OpenAI Agents SDK adapter | Only for OpenAI |
| `langchain>=0.3` | `pyproject.toml:64` (`[langchain]`) | LangChain adapter | Only for LangChain |
| `cryptography>=45.0` | `pyproject.toml:69` (`[attest]`), also in `[dev]` | Ed25519 event-chain attestation | Only for `continuum attest` |
| `psycopg>=3.2` | `pyproject.toml:72` (`[postgres]`) | PostgreSQL storage backend | Only for Postgres |
| **Dev / test tooling** (all in `pyproject.toml:33-50` `[dev]`) | | | Only for contributors |
| `pytest>=8.0`, `pytest-cov>=5.0`, `pytest-asyncio>=0.23` |  | Test runner + coverage + async MCP tests | Dev |
| `hypothesis>=6.0` |  | Property-based tests (hashing, models) | Dev |
| `ruff==0.16.3` |  | Lint + format (CI enforces `ruff check` + `ruff format --check`) | Dev |
| `mypy>=1.13` + `pydantic.mypy` |  | Strict type-check (CI runs `mypy src/continuum`) | Dev |

No other runtime dependencies. The CLI, storage, recovery engine, and checkpointing use only the Python standard library.

### 5. Verify the install

```bash
# CLI entrypoints
continuum --help
continuum-mcp --help             # needs [mcp] or [dev]

# One-command demo (process kill, hash-chain verify)
./try-it.sh demo                 # same as: python examples/crash_recovery_agent.py

# Full test suite (1252 passed on Python 3.13)
pytest -q                        # or: ./try-it.sh test
pytest --no-cov --tb=short -q    # faster, no coverage
pytest tests/test_events.py -v   # single file

# Lint and type-check (must pass for PRs)
ruff check src/ tests/ examples/
ruff format --check src/ tests/ examples/
mypy src/continuum

# Live Postgres contract tests (needs a running Postgres)
# docker run -d -p 5432:5432 -e POSTGRES_USER=continuum -e POSTGRES_PASSWORD=continuum -e POSTGRES_DB=continuum_test postgres:16
# CONTINUUM_TEST_POSTGRES_DSN=postgresql://continuum:continuum@localhost:5432/continuum_test pytest tests/test_storage_postgres.py tests/test_action_index.py -q
```

Two entrypoints are installed: `continuum` (CLI) and `continuum-mcp` (MCP server). The core library and CLI use only the standard library; the `mcp` extra is required solely for the server. See `CONTRIBUTING.md:1` for the full contributor workflow and `pyproject.toml:1` for the authoritative dependency list.

### Wiring a coding agent (the two-minute path)

For Claude Code, Gemini CLI, or Codex, you do not write Python and do not need a prompt file:

```bash
continuum start my-task --goal "What the agent should do"
continuum hooks install claude-code --with-gate   # also: gemini, codex
```

From then on every file the agent writes is captured as hash-chained evidence,
its session starts with an automatic status briefing, unclaimed side effects
registered in `.continuum/gate.json` are refused before they fire, and a fresh
session after any crash resumes with executable next steps. No CLAUDE.md required.

Minimal library example, record and recover:

```python
from continuum import EventType, Run, SQLiteStorage, project

store = SQLiteStorage("agent.db")
store.create_run(Run(run_id="run_4821", goal="Analyze 10,000 documents"))
store.append_event("run_4821", EventType.RUN_STARTED, {"goal": "Analyze 10,000 documents", "total": 10_000})

for i, doc in enumerate(documents):
    analyze(doc)
    store.append_event("run_4821", EventType.WORK_COMPLETED, {"doc": i})

# After a crash, a new process picks up exactly where it stopped:
state = project("run_4821", store.read_events("run_4821"))
print(state.progress.completed)            # already done, not repeated
print(store.verify_events("run_4821").ok)  # True, chain intact after the crash
```

**Run the proof yourself.** These scripts are the primary evidence, verified end to end rather than described:

```bash
python examples/crash_recovery_agent.py   # real process kill, real side effect
python examples/context_compaction.py     # transcript lost, checkpoint survives
python examples/model_switch.py           # Model A dies, Model B resumes safely
python scripts/mcp_smoke.py               # real subprocess, real JSON-RPC traffic
```

The `e2e-autonomy-test/` kit scripts a real invoice-batch task, a hard-kill mid-run, and a fresh resume session, then scores the outbox, ledger, and event chain out of band. Run 1 scored **7/7 mechanics** against a real Claude Code session, and the autonomy half was observed (an agent used the tools unprompted, refused to re-send verified invoices, and surfaced the `request_human` verdict). Full walkthrough and the open questions are in [references/quickstart.md](references/quickstart.md) and [references/e2e.md](references/e2e.md).

## How it works

CONTINUUM separates **LLM context** (temporary) from **durable task state** (permanent). Instead of saving conversation history, it constructs a semantic checkpoint, the minimum verified information required to continue.

![CONTINUUM how it works](docs/assets/architecture.svg)

The detailed explanation, the projection model, and the recovery context are in [references/architecture.md](references/architecture.md).

## Features

| Capability | What it gives you |
|:--|:--|
| Semantic checkpoints | Compact, versioned, inspectable state, not a transcript dump |
| Idempotent action ledger | Refuses duplicate external side effects; surfaces uncertain ones for reconciliation |
| Environment revalidation | Every checkpoint component verified against the current world before resume |
| Provenance-aware state | Agent-reported progress is marked `REQUIRES_REVIEW`, never self-certifying |
| Recovery engine | Seven recovery modes with a deterministic, sealed next-action contract |
| Deny-by-default MCP server | Nine tools, read-only/mutating split, caller allowlist |
| Framework adapters | Generic Python, OpenAI Agents SDK, LangGraph, and LangChain integrations |
| Secure planning loop | Two-signal observation verification escalates high-risk branches to REQUIRES_REVIEW |
| Periodic revalidation | Environment re-checked on a schedule, catching mid-run drift within one cycle |
| Tamper-evident log | Hash-chained event log (32 event types) with integrity verification |
| Enforcing gate | Unclaimed side-effect calls are refused before they fire; deny messages teach the claim protocol |
| Observation hooks | Every file a coding CLI writes becomes digest-verified evidence, outside model control |
| Session briefing | Fresh sessions learn run state deterministically at start - no prompt file |
| Reconciler probes | Registered commands settle uncertain side effects automatically; humans see only the rest |
| Executable guidance | Resume/validate render next steps as runnable commands, not statuses |
| Enforcing HTTP gateway | Outbound calls in any language require claims; responses settle them from reality |
| OpenTelemetry bridge | Tool-call spans from production tracing become evidence with zero code changes |
| Action index | Cross-run idempotency lookups are indexed reads, not full-log scans |

## Security Extension

CONTINUUM adds two additive security extensions on top of the existing recovery
and checkpoint substrate. They do not change resume, replay, or the existing
crash-time revalidation path.

- **Secure Planning Loop**: observations (for example a perception of a UI
  element) carry provenance and are verified by two independent signals
  (`verified` / `unverified` / `contested`). A plan branch gated on an
  observation is escalated to `REQUIRES_REVIEW` when it is high risk and the
  observation is not fully verified, or when an environment observation is
  contested. Verification decisions and branch resolutions are appended to the
  ledger as `PERCEPTION_OBSERVED` and `BRANCH_RESOLVED` events.
- **Periodic Revalidation**: reuses the recovery engine on a step interval
  (default 25) and on app switch, so mid-run environment drift is caught within
  one cycle instead of only at the next crash.

See [docs/PROBLEM.md](docs/PROBLEM.md) for the problem statement and honest
scope, [docs/RESULTS.md](docs/RESULTS.md) for results, and
[STATUS.md](STATUS.md) for the implementation status.

## Empirical Verification

CONTINUUM is verified not just with mock unit tests, but against real LLM agents, live protocol boundaries, and hard process crashes.

### Real Agent Testing (Claude Code, Gemini CLI, Kilo Code)

- **Claude Code (Opus 4.8) End-to-End Autonomy**: Driven across multi-session invoice-processing batches with mid-run `SIGKILL` hard process terminations. Resumed sessions cleanly queried `continuum_resume`, routed side effects through the two-phase intercept/complete ledger, and scored 7/7 on mechanics. The agent refused to duplicate verified outbox writes and respected the `request_human` safety verdict.
- **Drift-Hardened Deduplication**: Live agent testing revealed real-world prompt drift across sessions (argument field renames such as `target` vs `outbox_file`, and relative vs absolute paths). This prompted the implementation of canonical path normalization and token-based fallback deduplication in `ActionLedger.claim()`.
- **Gemini CLI and Kilo Code**: Both third-party clients connected over stdio JSON-RPC and invoked tools against the live SQLite store, validating multi-agent co-existence and authorization isolation.

### Protocol and Boundary Testing (MCP Inspector CLI)

- **Stdio Protocol Compliance**: Verified with `@modelcontextprotocol/inspector` in `--cli` mode driving real subprocess JSON-RPC 2.0 lifecycles across process deaths.
- **Deny-by-Default Security**: Mutating tools require explicit allowlisting (`CONTINUUM_MCP_MUTATING_CLIENTS`), while read-only tools (`validate`, `resume`, `list_actions`) remain ungated.
- **Anti-Self-Certification**: External agent claims written via MCP are signed with `Origin.EXTERNAL_AGENT` provenance and degraded to `REQUIRES_REVIEW` (`safe: false`), preventing an agent from validating its own unverified work.

### Crash Recovery and Self-Healing

- **WAL Sidecar Auto-Recovery**: Hard-killing a server process (`kill -9`) can leave SQLite in an inconsistent state with orphaned `-wal` and `-shm` sidecars. The MCP server startup incorporates single-retry self-healing that clears stale sidecars and reopens cleanly.

### Automated Test Suite and Benchmarks

- **1224 tests passing, 13 skipped** on Python 3.11, 3.12, and 3.13 (including unit, `hypothesis` property-based, concurrency, and adversarial tests).
- **CONTINUUM-Bench**: `continuum benchmark` executes in-process recovery benchmarks across five scenarios (`process_crash`, `dataset_change`, `unknown_side_effect`, `partial_completion`, `early_crash`), proving 0 duplicate work, 0 duplicate side effects, and automatic detection of stale environment dependencies.

### Adversarial Audit of the MCP Surface

The MCP server was audited end to end over the live stdio protocol, with every
tool result checked against the SQLite store rather than taken at its word. The
self-certification gate, the two-phase ledger, crash-mid-action reconciliation,
tamper-evidence, and deny-by-default authorization all held. Three defects were
found and fixed: environment drift was detected but did not invalidate state,
`list_actions` under-reported an interrupted row, and the WAL sidecar recovery
could delete committed transactions. Method, per-claim results, and reproduction
steps are in [test.md](test.md).

## MCP Integration

CONTINUUM ships an MCP server so an agent can record progress, checkpoint, and route external side effects through the ledger without embedding the library:

```bash
uv pip install -e ".[mcp]"
CONTINUUM_MCP_MUTATING_CLIENTS=your-client-name continuum-mcp
```

Eleven tools over stdio. Three are read-only (`continuum_validate`, `continuum_resume`, `continuum_list_actions`); eight mutate. Side effects are two-phase (claim, perform, complete), and mutating tools deny by default behind an allowlist. Agent-reported state is recorded with `Origin.EXTERNAL_AGENT` provenance and marked `REQUIRES_REVIEW`. Verification details, including crash recovery at startup and the end to end Claude Code test, are in [references/mcp.md](references/mcp.md). The authentication limitation is covered in [references/architecture.md](references/architecture.md) (MCP server and Security sections), and the MCP narrative is in [references/quickstart.md](references/quickstart.md). If a registered server reports `CONNECTION_CLOSED`, the cause is almost always `PATH` resolution rather than the server itself: [docs/api/mcp.md](docs/api/mcp.md#troubleshooting) has the diagnosis and two remedies.

## Framework Integration

CONTINUUM plugs into agent frameworks without becoming one. Nine adapters ship in `src/continuum/adapters/` (one in-process facade plus eight integrations), all optional installs so the core stays standard-library-only:

| Adapter | Class | Notes |
|:--|:--|:--|
| Generic Python agent | `GenericAgentAdapter` | In-process facade; writes trusted (`Origin.DETERMINISTIC`) state. |
| Filesystem sandbox | `FilesystemSandboxAdapter` | Local directory sandbox, no external service, default for docs and CI. |
| Python in-process | `PythonInProcAdapter` | Runs Python in a temp workdir, records via ledger. |
| Container | `ContainerAdapter` | Docker backed, guarded skip when `docker` is absent. |
| Browser | `BrowserAdapter` | Playwright backed, guarded skip when not installed. |
| Kubernetes | `KubernetesAdapter` | `kubectl` backed, guarded skip when not configured. |
| OpenAI Agents SDK | `OpenAIAgentAdapter` | Experimental. Hooks `ToolContext` / `RunHooks`; optional `openai-agents`. |
| LangGraph | `LangGraphAgentAdapter` | Experimental. Wraps a `StateGraph`; optional `langgraph`. |
| LangChain | `LangChainAgentAdapter` | Experimental. Drops `checkpoint_node` into an LCEL `Runnable` pipeline and the `create_agent` tool-calling loop; optional `langchain`. |

Each adapter records progress and side effects through the ledger and routes external effects through the two-phase intercept/complete protocol. The framework adapters are newer than the generic facade, but each now has end-to-end integration tests (`tests/test_integration_langgraph.py`, `tests/test_integration_langchain.py`, and `tests/test_integration_langchain_agent.py` for a real `create_agent` tool-calling loop) covering checkpoint durability, exactly-once side effects, and crash-after-checkpoint resume. All three framework adapters (LangChain, LangGraph, OpenAI Agents SDK) have now
been driven against a **live OpenRouter model** (`examples/langchain_real_llm.py`,
`examples/langgraph_real_llm.py`, `examples/openai_real_llm.py`; recorded in
STATUS.md), where the runs surfaced and then closed an LLM argument-drift dedup gap
via an explicit idempotency key and two OpenAI-adapter schema/context bugs. Each
adapter also has a `examples/*_real_llm_crash.py` harness that proves the
hard-crash contract: a mid-side-effect `os._exit(137)` leaves the side effect
uncertain and blocks resume until a human reconciles it. `examples/multitool_real_llm.py`
is a richer live demo where one prompt orchestrates lookup, notify, and ticket tools
through the LangGraph adapter, showing exactly-once survives the model's argument
drift. Treat them as experimental until their adapter-specific tests cover the full
crash and resume matrix. Full usage, with runnable examples for every adapter, is in
[references/adapters.md](references/adapters.md).

Three further production frameworks are covered by thin, SDK-free hook
surfaces in [`adapters/thin.py`](src/continuum/adapters/thin.py), each routing
through the same claim/complete ledger with stable keys:

| Framework | Interception surface | Entry point |
|:--|:--|:--|
| CrewAI | global before/after tool-call hooks | `install_crewai_hooks(storage, run_id)` |
| AutoGen core | `FunctionTool.run_json` wrapped in place | `wrap_autogen_tool(tool, storage, run_id)` |
| Pydantic AI | async Hooks capability | `Agent(capabilities=[wrap_pydantic_ai_hooks(storage, run_id)])` |

For stacks none of these reach, two transport-level seams close the gap:
`continuum gateway` enforces claims on outbound HTTP from any language, and
`continuum.otel.make_span_processor(storage)` turns existing OpenTelemetry
tool spans into evidence (`pip install continuum-agent[otel]`).

### Live LLM validation (real model via OpenRouter)

All three framework adapters were driven against a live `gpt-4o-mini` through
OpenRouter (key from `OPENROUTER_API_KEY`, never written to disk). Each was proven
two ways: a soft resume (exactly-once side effect across a second clean invocation)
and a hard crash (`os._exit(137)` mid-side-effect, then a fresh process asserts the
run is blocked as uncertain). A richer `examples/multitool_real_llm.py` demo has one
prompt orchestrate `lookup_order` + `notify_customer` + `create_ticket` through the
LangGraph adapter.

| Adapter    | Soft resume (exactly-once)             | Hard crash (resume blocked)       |
|------------|----------------------------------------|-----------------------------------|
| LangChain  | PASS, 1 side effect, `resume` safe     | PASS, `request_human`, 1 uncertain |
| OpenAI SDK | PASS, 1 side effect, `request_human`*  | PASS, `request_human`, 1 uncertain |
| LangGraph  | PASS, 1 side effect, `resume` safe     | PASS, `request_human`, 1 uncertain |

\* The OpenAI adapter yields `request_human` even on a clean soft resume because it
records `Origin.EXTERNAL_AGENT`: an agent must not self-certify its own unverified
work. That is expected and safe. LangChain and LangGraph use `Origin.DETERMINISTIC`
and resume cleanly.

Two OpenAI-adapter bugs that only surface with a real model were found and fixed:
the tool JSON schema was emitted with no `type` key (OpenRouter rejected it), and the
context parameter was dropped from the inspectable signature, which bypassed
interception and let the side effect fire twice. The live runs also confirmed the
idempotency lesson: a stable business key (for example `ticket:O-9`) is required,
because a key derived from the model's rendered arguments does not dedupe the model's
argument drift and produced a duplicate ticket. Full run logs are in STATUS.md.

### Resuming agent- or MCP-reported runs

State reported over MCP, or through the OpenAI adapter, is recorded with `Origin.EXTERNAL_AGENT` provenance, which the validator marks `REQUIRES_REVIEW`. That is intentional: an agent must not validate its own unverified work. The consequence is that such runs resolve to `request_human` on `continuum resume` until a human has eyeballed them.

Runs started through the LangGraph or LangChain adapter use `Origin.DETERMINISTIC` provenance (the adapter is the orchestrator starting the run on CONTINUUM's behalf), so a consistent run resumes (`RESUME`) without a human in the loop.

To clear that review and resume, confirm the run as the operator:

```bash
continuum confirm <run_id>   # records REVIEW_CONFIRMED, then re-assesses
continuum resume <run_id>    # now reports RESUME
```

Over MCP the equivalent is the `continuum_confirm` tool followed by `continuum_resume`. Confirmation is a one-time, human-attested event; it is the escape hatch for the self-certification safety so an externally-driven run is never permanently stuck.

## Core Concepts

The deep reference for each concept lives in [references/concepts.md](references/concepts.md).

- **Semantic Checkpoints** - a compact, versioned representation of what the agent needs to continue.
- **State Validation** - every component independently verified; staleness propagates through the dependency graph.
- **Idempotent Action Ledger** - external side effects tracked and de-duplicated; uncertain outcomes raise instead of silently retrying.
- **Recovery Modes** - `RESUME`, `REPAIR_AND_RESUME`, `ROLLBACK`, `WAIT`, `REQUEST_HUMAN`, `ABORT` (plus `REPLAN`).
- **Recovery Contract** - a deterministic, integrity-sealed, gated next action.

## Architecture

The system is built on immutable Pydantic v2 models with a cryptographic hash chain. State is projected from an append-only event log by a pure fold, not stored and mutated. The full reference, including the data model, event log, projection, extraction, versioning, durable storage, checkpointing, recovery context, state validation, action ledger, recovery engine, and security model, is in [references/architecture.md](references/architecture.md). A complete system diagram and enumerated reference (tools, recovery modes, policies, reconcilers) is in [references/architecture-diagram.md](references/architecture-diagram.md).

Key guarantees: append-only events, atomic sequence allocation, durability on `append_event` return, write races fail loudly, and corruption is refused rather than returned.

### Project structure

CONTINUUM is one library (`src/continuum`, about 80 Python files) plus a large test suite (68 files, 1038 tests). The modules are layered and all append to and replay one hash-chained event log:

| Module | LOC | Role |
|:--|--:|:--|
| `events.py` | 391 | Append-only, hash-chained event log and `verify()` |
| `state/` | 1,637 | Projection (`semantic.py`), validation (`validator.py`), extraction |
| `storage/` | 1,690 | `SQLiteStorage` (v2 schema), `postgres.py`, `migrations.py` |
| `actions/` | 1,183 | Idempotent action ledger, reconciliation, claim/complete |
| `checkpoint/` | 924 | Policy-driven checkpoints |
| `recovery/` | 699 | Engine (max-severity wins), planner, sealed contract |
| `adapters/` | 1,596 | Generic, LangChain, LangGraph, OpenAI Agents SDK |
| `mcp/` | 1,334 | Ten stdio tools plus `authz.py` (token auth, allowlist) |
| `serve/` | 739 | Language-agnostic newline-JSON sidecar mirroring MCP |
| `cli/` | 1,218 | `argparse` commands, exit codes as verdict |
| `benchmark/` | 440 | CONTINUUM-Bench scenario harness |
| `environment/` | 514 | Snapshots and diffs |
| `security/` | 608 | Provenance, trust gate, revalidation (in progress) |
| `interchange/` | 312 | B4 portable recovery-state JSON envelope |
| `concurrency/` | 255 | B2.2 lease and distributed-lock coordinator |
| `plugins/` | 174 | Registry and capability seams |
| `models.py`, `observability.py`, `__init__.py` | ~1,100 | Shared models, metrics, public surface |

Three entry points, all from `main`: the `continuum` CLI, the `continuum-mcp` server, and the `continuum serve` sidecar. `storage/`, `state/`, `adapters/`, `mcp/`, `cli/`, `actions/`, and `checkpoint/` hold roughly 72% of the core and are the mature, heavily-tested layers. `security/`, `storage/postgres.py`, `migrations.py`, and `concurrency/` are committed but newer: the Postgres backend is unverified against a live server in this environment (its tests skip without `CONTINUUM_TEST_POSTGRES_DSN` / `psycopg`). `interchange/` is done and tested. The full data model, projection, and recovery reference is in [references/architecture.md](references/architecture.md).

## API and CLI

Python surface (`EventType`, `Run`, `SQLiteStorage`, `diff_states`, `project`) and the adapter API are documented with runnable examples in [references/api.md](references/api.md). The CLI is the same surface in shell form:

```bash
continuum runs                                   # list runs
continuum inspect <run_id>                       # semantic state
continuum validate <run_id> --env dataset=v4     # validate, read-only
continuum resume <run_id> --env dataset=v4       # recovery decision + contract + next steps
continuum checkpoint <run_id>                    # force a checkpoint, mutates
continuum actions <run_id>                       # external side effects
continuum reconcile <run_id>                     # settle uncertain effects with probes
continuum complete <run_id>                      # close a run as done, from the keyboard
continuum verify <run_id>                        # re-audit the event hash chain
```

### Wiring into harnesses

CONTINUUM meets agents where they already run. All wiring is host-side; the model's cooperation is optional.

```bash
# Coding CLIs with lifecycle hooks: evidence capture, session briefing,
# and claim enforcement, installed in one command.
continuum hooks install claude-code --with-gate   # also: gemini, codex

# Frameworks without hooks: the enforcing HTTP proxy. Point outbound calls
# at localhost; unclaimed requests are refused, claims are settled from the
# real upstream response.
continuum gateway --port 8765                     # routes: .continuum/gateway.json

# Production stacks emitting OpenTelemetry: spans become evidence.
provider.add_span_processor(continuum.otel.make_span_processor(storage))

# Anything MCP-capable: the original ten-tool server.
continuum-mcp                                     # via .mcp.json
```

Optional registries live beside your code and are data, not code:
`.continuum/gate.json` (side-effect tools + stable-key templates),
`.continuum/reconcilers.json` (probes that check external systems),
`.continuum/gateway.json` (upstream routes).

Every command accepts `--json`, and the read-only commands never write, so they are safe against a live database while an agent is mid-run. Exit codes are a safety contract (only a verified-safe run exits 0). The full command list, exit-code table, and state-diff output are in [references/cli.md](references/cli.md).

## Roadmap

| Phase | Component | Status |
|:-----:|:--|:--|
| 1-11 | Data models, semantic state, persistence, checkpointing, validation, action ledger, recovery engine, CLI, crash-recovery examples, environment snapshots/diffs, framework adapters | Complete |
| 12 | Benchmark suite (CONTINUUM-Bench) | Complete (minimal harness) |
| 13 | Cloud API (FastAPI + PostgreSQL) | Planned |
| 14 | Dashboard | Complete (`continuum dashboard`) |
| 15+ | Enforced durability: observation hooks, gate, session briefing, reconciler probes, enforcing gateway, OTel bridge, action index, executable guidance, multi-client installers | Complete (see issue #213) |

Beyond the original plan: the MCP server, MCP authorization layer, provenance and anti-self-certification, community files, schema versioning, and a bounded recovery context are shipped. The design for CONTINUUM-Bench is in [references/bench.md](references/bench.md). See [STATUS.md](STATUS.md) for the verified-vs-believed breakdown and open correctness bugs.

## What CONTINUUM Is Not

| Not this | This instead |
|:--|:--|
| An LLM | A reliability layer for agents that use LLMs |
| An agent framework | A recovery layer that plugs into any framework |
| A vector database | Structured semantic state, not embeddings |
| A RAG system | Verified checkpoints, not retrieval-augmented memory |
| A workflow engine | A recovery layer, not an orchestrator |

The core abstraction: `semantic state + environment validation + action reconciliation = safe recovery`.

## Related work

CONTINUUM sits at the overlap of durable execution, idempotent side-effect tracking, and crash recovery for LLM agents. The surrounding literature is mostly engineering writing, with a few recent preprints that examine the same failure modes directly.

### Foundations

- **Idempotency keys.** The standard "do not do it twice" mechanism for external systems. See Stripe's [idempotent requests](https://docs.stripe.com/api/idempotent_requests) and the [AWS Lambda Powertools idempotency utility](https://docs.aws.amazon.com/lambda/latest/dg/powertools-idempotency.html).
- **Transaction outbox pattern.** Write intent and effect record in one durable step, then dispatch, so a crash cannot lose an in-flight side effect ([Chris Richardson's write-up](https://microservices.io/patterns/data/transactional-outbox.html)).
- **Saga pattern and compensating actions.** A sequence of local steps where each has a semantic undo, so a failure can be repaired without an ACID rollback. Relevant to CONTINUUM's `COMPENSATED` action state and dependency-safe repair ([saga pattern](https://microservices.io/patterns/data/saga.html)).
- **Durable execution engines.** [Temporal](https://docs.temporal.io/), Restate, and DBOS persist a journal of completed steps and replay it for exactly-once semantics across crashes and redeploys.
- **Anthropic, Building Effective Agents (2024).** Workflow and orchestration patterns that frame agents as stateful processes worth making durable ([research post](https://www.anthropic.com/research/building-effective-agents)).

### Academic context

Recent preprints that measure or model the same reliability gaps CONTINUUM targets (all arXiv links verified live):

- Khan, *Resume Means Resume: A Machine-Checked Conformance Contract for Checkpoint, Interrupt, and Resume Semantics in Workflow Persistence Layers*, [arXiv:2608.03836](https://arxiv.org/abs/2608.03836) (2026). Proves a reference resume contract in TLA+ and measures that widely deployed frameworks re-execute durably recorded work after a real SIGKILL and cannot resume after a mid-node crash, the exact defects CONTINUUM's ledger and recovery gate exist to prevent.
- Chang, Geng, and Chang, *Mnemosyne: Agentic Transaction Processing for Validating and Repairing AI-generated Workflows*, [arXiv:2607.00269](https://arxiv.org/abs/2607.00269) (2026). Treats generated actions as untrusted proposals admitted only against a declared constraint set, with an append-only transition log and dependency-safe compensation. Close to CONTINUUM's deny-by-default admission and provenance model.
- Liu, Zhao, Shang, and Shen, *Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems*, [arXiv:2604.14228](https://arxiv.org/abs/2604.14228) (2026). Finds that most agent code is operational infrastructure (context management, permission systems, append-oriented session storage) rather than model logic, the layer CONTINUUM lives in.
- Zheng, Yang, Zhang, and Quinn, *ACRFence: Preventing Semantic Rollback Attacks in Agent Checkpoint-Restore*, [alphaXiv:2603.20625v1](https://www.alphaxiv.org/overview/2603.20625v1) (2026). Identifies checkpoint restore as a rollback of agent memory that does not roll back external effects, demonstrates 10 of 10 duplicate commits with Claude Code CLI and Qwen3-32B, and proposes an MCP proxy with an effect log and a semantic analyzer for replay, block, or fork. Evaluation of the testbed is implemented, the ACRFence mitigation itself is proposed but not yet evaluated in the paper.
- Tavori, Bremler-Barr, Levy, and Lavi, *RetryGuard: Preventing Self-Inflicted Retry Storms in Cloud Microservices Applications*, [arXiv:2511.23278](https://arxiv.org/abs/2511.23278) (2025). Shows default retry patterns amplify cost and load under failure, motivating global retry budgets rather than per-call loops.
- Debenedetti et al., *CaMeL: Defeating Prompt Injections by Design*, [arXiv:2503.18813](https://arxiv.org/abs/2503.18813) (2025). A system-level control- and data-flow-integrity layer that provably stops untrusted data from steering an agent; the canonical precedent for CONTINUUM's rule that externally-asserted state cannot self-certify its own safety.
- LogAct, *LogAct: Enabling Agentic Reliability via Shared Logs*, [arXiv:2604.07988](https://arxiv.org/abs/2604.07988) (2026). Frames agent fault tolerance as write-ahead logging over a shared log and argues saga-style compensation fails for non-invertible agent actions, the same reasoning behind CONTINUUM's ledger-over-sagas choice.
- *Crab: A Semantics-Aware Checkpoint/Restore Runtime for Agent Sandboxes*, [arXiv:2604.28138](https://arxiv.org/abs/2604.28138) (2026). Measures how divergence between a restored environment and the original execution derails recovered agents, empirical support for refusing to resume until state is revalidated against the world.
- Feng et al., *Get Experience from Practice: LLM Agents with Record & Replay (AgentRR)*, [arXiv:2505.17716](https://arxiv.org/abs/2505.17716) (2025). Uses check functions as a trusted computing base verifying preconditions during replay, vocabulary CONTINUUM adopts for documenting what makes a resume unsafe.
- Miculicich et al., *VeriGuard: Enhancing LLM Agent Safety via Verified Code Generation*, [arXiv:2510.05156](https://arxiv.org/abs/2510.05156) (2025). Splits expensive verification offline from millisecond online action monitoring, the same offline/online split as CONTINUUM's policy evaluation versus background checkpoint writes.
- Souza et al., *PROV-AGENT: Unified Provenance for Tracking AI Agent Interactions in Agentic Workflows*, [arXiv:2508.02866](https://arxiv.org/abs/2508.02866) (2025). Extends W3C PROV to agent interactions, a standard-compliant shape for the provenance CONTINUUM already records per event.
- Shi et al., *Progent: Securing AI Agents with Privilege Control*, [arXiv:2504.11703](https://arxiv.org/abs/2504.11703) (2025). Per-task privilege policies enforced at the tool boundary, complementary to pairing policy checks with ledger claims.
- Wang, Poskitt, and Sun, *AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents*, [arXiv:2503.18666](https://arxiv.org/abs/2503.18666) (2026). A trigger/predicate/enforcement DSL for runtime constraints, a declarative shape recovery-refusal rules could take.
- Cemri et al., *Why Do Multi-Agent LLM Systems Fail?*, [arXiv:2503.13657](https://arxiv.org/abs/2503.13657) (2025). The MAST failure taxonomy, useful for stating which failure classes CONTINUUM mechanically prevents (duplicate execution, lost state, unverifiable claims) versus merely detects.
- Yao et al., *tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains*, [arXiv:2406.12045](https://arxiv.org/abs/2406.12045) (ICLR 2025). Verifies outcomes against database end-state rather than model judgment and defines pass^k consistency, the right yardstick for durability under injected crashes.
- Packer et al., *MemGPT: Towards LLMs as Operating Systems*, [arXiv:2310.08560](https://arxiv.org/abs/2310.08560) (2023). The OS analogy legitimizes CONTINUUM's framing of its log as a journal and its checkpoints as snapshots.

All arXiv links above were resolved against the arXiv API on 2026-08-22.

## Status and limitations

- **Tested**: 1063 tests passing, 10 skipped (a few skip without optional services such as Postgres; see [STATUS.md](STATUS.md)). The MCP surface has also been audited adversarially over the live protocol; see [test.md](test.md).
- **Not on PyPI.** Install from a clone (see Quick Start).
- **MCP caller authentication is optional.** When `CONTINUUM_MCP_TOKEN` is set, the server refuses every mutating tool unless the caller presents that shared secret in the `initialize` handshake's `_meta.authToken`. Without it, authorization is by declared identity only (the historical default, preserved for local single-user use). Tracked as [#1](https://github.com/Cyrax321/CONTINUUM/issues/1).
- **Confirming self-reported state over MCP needs its own secret.** `continuum_confirm` refuses every caller until the operator sets `CONTINUUM_MCP_CONFIRM_TOKEN`, because an agent allowed to record progress must not also be able to confirm it (issue [#201](https://github.com/Cyrax321/CONTINUUM/issues/201)). The default path stays human-driven: run `continuum confirm <run_id>` on the host.
- **Unbuilt components**: Cloud API (Phase 13).
- **Framework adapters are experimental.** The OpenAI Agents SDK and LangGraph adapters are newer than the generic facade and do not yet carry the same crash-and-resume verification coverage. Prefer `GenericAgentAdapter` for production recovery until their adapter-specific tests cover the full recovery matrix.
- **Agent/MCP runs need an explicit confirm before auto-resume.** Because externally-reported state is `REQUIRES_REVIEW`, `continuum resume` returns `request_human` until a human runs `continuum confirm <run_id>` (or the MCP `continuum_confirm` tool). This is by design, not a bug; see [Framework Integration](#framework-integration).
- **e2e autonomy test series** (issue [#6](https://github.com/Cyrax321/CONTINUUM/issues/6)): Three full Claude Code runs scored 7/7 mechanics with unprompted recovery behavior observed. Defensive token-based fallback and path normalization bridge argument drift. Further test iterations across diverse prompt styles remain open.

For a full account of what is verified, believed, and neither, see [STATUS.md](STATUS.md). The current set of open correctness bugs (a 2026-08-12 code audit) is tracked there.

## Contributing

Contributions are welcome. This project is open source under Apache 2.0 and deliberately built to be extended: by researchers validating the recovery semantics, by engineers porting the ledger or MCP server to other frameworks or languages, and by anyone turning the planned roadmap into reality. A good place to start is the `good first issue` label on the [issue tracker](https://github.com/Cyrax321/CONTINUUM/issues), or the open correctness bugs listed in STATUS.md.

Open an issue before submitting large PRs. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution guide, including the [Code of Conduct](CODE_OF_CONDUCT.md).

### Contributors

<a href="https://github.com/Cyrax321"><img src="docs/contributors/cyrax321.png" width="60" alt="Cyrax321" /></a>
  <a href="https://github.com/dchaudhari7177"><img src="docs/contributors/dchaudhari7177.png" width="60" alt="Dipak Chaudhari" /></a>
  <a href="https://github.com/lesbass"><img src="docs/contributors/lesbass.png" width="60" alt="Stefano Maffeis" /></a>
  <a href="https://github.com/as950118"><img src="docs/contributors/as950118.png" width="60" alt="heonjinjeong" /></a>
  <a href="https://github.com/abyyxhek"><img src="docs/contributors/abyyxhek.png" width="60" alt="Abishek" /></a>


## License

Apache 2.0 - see [LICENSE](LICENSE).

---

Deep reference material:

- [references/concepts.md](references/concepts.md) - semantic checkpoints, validation, ledger, recovery modes, contract
- [references/architecture.md](references/architecture.md) - data model, event log, projection, storage, checkpointing, recovery engine, security, project structure
- [references/api.md](references/api.md) - Python and adapter API
- [references/adapters.md](references/adapters.md) - framework adapter usage (Generic, OpenAI, LangGraph, LangChain) with runnable examples
- [references/cli.md](references/cli.md) - full CLI command list, exit codes, state diff
- [references/quickstart.md](references/quickstart.md) - install, examples, the proof scripts
- [references/e2e.md](references/e2e.md) - end to end autonomy test walkthrough
- [references/mcp.md](references/mcp.md) - MCP server status, verification, open questions
- [references/bench.md](references/bench.md) - CONTINUUM-Bench design
