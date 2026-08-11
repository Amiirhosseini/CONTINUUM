# CONTINUUM

> A lightweight, framework-agnostic semantic recovery layer for long-running AI agents.

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue?style=flat-square" alt="License" /></a>
  <a href="https://pydantic.dev"><img src="https://img.shields.io/badge/pydantic-v2-E92063?style=flat-square&logo=pydantic&logoColor=white" alt="Pydantic v2" /></a>
  <a href="https://cyrax321.github.io/CONTINUUM/"><img src="https://img.shields.io/badge/website-live-E06D53?style=flat-square" alt="Website" /></a>
  <img src="https://img.shields.io/badge/tests-607_passing-22C55E?style=flat-square" alt="607 tests" />
</p>

---

```
Agent crashes.
Context disappears.
CONTINUUM remembers what actually matters.
```

---

## The Problem

Modern AI agents perform long-running tasks — hundreds of LLM calls, tool invocations, API sessions, file mutations, database writes. When they crash (and they will crash), the typical response is to replay everything from scratch.

That means duplicated work, duplicated API calls, duplicated side effects, higher cost, lost decisions, and inconsistent state.

CONTINUUM investigates a narrower question:

> Can an agent resume safely from a compact semantic representation of its task state, while independently verifying whether that state is still valid?

This is not a generic agent framework. Not a memory system. Not a workflow engine.

CONTINUUM's differentiator is three-part: **semantic checkpointing**, **independent environment revalidation**, and **provenance-aware state**.

---

## How It Works

CONTINUUM separates **LLM context** (temporary) from **durable task state** (permanent). Instead of saving conversation history or full agent state, it constructs a **semantic checkpoint** — the minimum verified information required to continue the task.

```
                   AI AGENT
                      |
                      v
              +-----------------+
              |  CONTINUUM SDK  |
              +--------+--------+
                       |
           +-----------+-----------+
           v           v           v
        State        Action      Evidence
        Engine       Ledger      Registry
           |           |           |
           +-----------+-----------+
                       v
              Semantic Checkpoint
                       |
                       v
               Durable Storage
                       |
             +---------+---------+
             v                   v
        Environment          Recovery
        Validation              |
             |                  v
             +--------------> Resume
```

---

## Quick Start

> Not published to PyPI yet. Install from a clone:
>
> ```bash
> uv venv
> uv pip install -e ".[dev]"    # library, CLI, and test tooling
> uv pip install -e ".[mcp]"    # adds the MCP server (optional)
> ```
>
> Two entrypoints are installed: `continuum` (the CLI) and `continuum-mcp` (the MCP server). The core library and CLI use only the standard library.

```python
from continuum import EventType, Run, SQLiteStorage, project

store = SQLiteStorage("agent.db")
store.create_run(Run(run_id="run_4821", goal="Analyze 10,000 documents"))
store.append_event("run_4821", EventType.RUN_STARTED, {"goal": "...", "total": 10_000})

for i, doc in enumerate(documents):
    analyze(doc)
    store.append_event("run_4821", EventType.WORK_COMPLETED, {"doc": i})
```

The process dies. A new one picks up exactly where it stopped:

```python
store = SQLiteStorage("agent.db")
state = project("run_4821", store.read_events("run_4821"))

print(state.progress.completed)  # 3421 — already done, not repeated
print(store.verify_events("run_4821").ok)    # True — chain intact

for i, doc in enumerate(documents[state.progress.completed:], state.progress.completed):
    ...
```

### Run the proof yourself

Two scripts are the primary evidence, both verified end to end:

```bash
python examples/crash_recovery_agent.py   # real process kill, real side effect
python scripts/mcp_smoke.py               # real subprocess, real JSON-RPC traffic
```

Both exit non-zero if their guarantees fail.

---

## Core Concepts

### Semantic Checkpoints

Not a conversation dump. A compact, versioned tree of verified goals, decisions, findings, evidence, and pending tasks.

### State Validation

Every checkpoint component is checked against the live environment before resume. Staleness propagates: dependency → evidence → finding → decision.

### Idempotent Action Ledger

7 action states. Two-phase claim/complete protocol. Raises UnknownSideEffect on interrupted actions rather than guessing.

### Recovery Contracts

Deterministic, sealed with integrity hash. Names exactly one next permitted action.

---

## MCP Server

CONTINUUM ships an MCP server so an agent can record progress, checkpoint, and route external side effects through the ledger without embedding the library.

Nine tools over stdio:

| Tool | Type | Purpose |
|:--|:--|:--|
| `continuum_record_progress` | mutating | Record task progress; creates run on first call |
| `continuum_checkpoint` | mutating | Save durable semantic checkpoint |
| `continuum_intercept_action` | mutating | Claim ledger entry; answers "may I?" |
| `continuum_complete_action` | mutating | Report side effect succeeded |
| `continuum_fail_action` | mutating | Report side effect failed or uncertain |
| `continuum_reconcile_action` | mutating | Settle unknown action with evidence |
| `continuum_validate` | read-only | Check if state is still trustworthy |
| `continuum_resume` | read-only | Get recovery decision and contract |
| `continuum_list_actions` | read-only | List side effects; flag unresolved |

**Authorization:** Mutating tools require caller allowlist from `CONTINUUM_MCP_MUTATING_CLIENTS` env var or `.continuum/mcp-policy.json`. Read-only tools are open to all.

---

## CLI

Fourteen commands with safety-contract exit codes:

| Code | Meaning |
|:--|:--|
| 0 | verified safe to resume |
| 10 | recoverable, repairs required |
| 20 | human must decide |
| 30 | not safe to resume |

```bash
continuum init                    # create storage
continuum inspect run_4821         # view semantic state
continuum validate run_4821        # check against environment
continuum resume run_4821          # get recovery decision
continuum actions run_4821         # list side effects
```

---

## Architecture

### Data Model

Built on immutable, frozen Pydantic v2 models with cryptographic hash chains:

- Goal, Progress, PlanStep[], Decision[], Finding[], Evidence[], PendingWork[], Approval[], ExternalDependency[], ModelState

### Event Log

Append-only, hash-chained event stream. Source of truth for every run. 29 event types covering the full lifecycle.

### State Projection

Pure fold over event prefix. Reproducible and prefix-closed (both tested).

### Storage

SQLite with WAL, `synchronous=FULL`, `IMMEDIATE` transactions. Schema v2 with `UNIQUE(run_id, sequence)` backstop.

---

## Project Status

| Phase | Component | Status |
|:--|:--|:--|
| 1 | Data models + Event system | Complete |
| 2 | Semantic state representation | Complete |
| 3 | SQLite persistence | Complete |
| 4 | Checkpoint creation | Complete |
| 5 | State validation | Complete |
| 6 | Action ledger + Idempotency | Complete |
| 7 | Recovery engine | Complete |
| 8 | CLI | Complete |
| 9 | Crash recovery examples | Planned |
| 10 | Environment snapshots and diffs | Complete |
| 11 | Framework adapters | Planned |
| 12 | Benchmark suite | Planned |
| 13 | Cloud API | Planned |
| 14 | Dashboard | Planned |

**607 tests passing** — verified green on Python 3.11, 3.12, 3.13, plus lint (`ruff`) and strict type-check (`mypy`).

---

## Development

**Prerequisites**: Python 3.11+

```bash
git clone https://github.com/Cyrax321/CONTINUUM.git
cd CONTINUUM
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

```bash
pytest                    # Run all tests
pytest --cov              # With coverage
ruff check src/ tests/    # Lint
mypy                      # Type check
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

Built by [Cyrax321](https://github.com/Cyrax321). Open source, not AI-generated marketing.
