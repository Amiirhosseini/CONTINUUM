<p align="center">
  <img src="https://img.shields.io/badge/CONTINUUM-Semantic_Recovery-000000?style=for-the-badge&labelColor=0D1117&color=58A6FF" alt="CONTINUUM" />
</p>

<h1 align="center">CONTINUUM</h1>

<p align="center">
  <strong>Agents that can lose their context without losing their work.</strong>
</p>

<p align="center">
  <em>A lightweight, framework-agnostic semantic recovery layer for long-running AI agents.</em>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue?style=flat-square" alt="License" /></a>
  <a href="https://github.com/Cyrax321/CONTINUUM/actions"><img src="https://img.shields.io/badge/CI-passing-brightgreen?style=flat-square&logo=github-actions&logoColor=white" alt="CI" /></a>
  <a href="https://pydantic.dev"><img src="https://img.shields.io/badge/pydantic-v2-E92063?style=flat-square&logo=pydantic&logoColor=white" alt="Pydantic v2" /></a>
  <a href="https://github.com/Cyrax321/CONTINUUM/stargazers"><img src="https://img.shields.io/github/stars/Cyrax321/CONTINUUM?style=flat-square&color=FFD700" alt="Stars" /></a>
</p>

---

```
Agent crashes.
Context disappears.
CONTINUUM remembers what actually matters.
```

---

## The Problem

Modern AI agents perform long-running tasks — hundreds of LLM calls, tool invocations, API sessions, file mutations, database writes. When they crash (and they *will* crash), the typical response is to replay everything from scratch.

That means **duplicated work**, **duplicated API calls**, **duplicated side effects**, **higher cost**, **lost decisions**, and **inconsistent state**.

CONTINUUM solves a narrower, harder question:

> **Can an agent resume safely from a compact semantic representation of its task state, while independently verifying whether that state is still valid in the current environment?**

---

## How It Works

CONTINUUM separates **LLM context** (temporary) from **durable task state** (permanent). Instead of saving conversation history or full agent state, it constructs a **Semantic Checkpoint** — the minimum verified information required to continue the task.

```
                   AI AGENT
                      │
                      ▼
              ┌───────────────┐
              │ CONTINUUM SDK │
              └───────┬───────┘
                      │
          ┌───────────┼────────────┐
          ▼           ▼            ▼
       State        Action       Evidence
       Engine       Ledger       Registry
          │           │            │
          └───────────┼────────────┘
                      ▼
              Semantic Checkpoint
                      │
                      ▼
               Durable Storage
                      │
            ┌─────────┴─────────┐
            ▼                   ▼
       Environment          Recovery
       Validation              │
            │                  ▼
            └────────────► Resume
```

---

## Quick Start

### Installation

```bash
pip install continuum-agent
```

### 30-Second Demo

```python
from continuum import Continuum

# Initialize with local SQLite storage
runtime = Continuum("agent.db")

# Start a long-running task
run = runtime.start(goal="Analyze 10,000 documents for evidence supporting hypothesis X")

# Process items...
for doc in documents:
    result = analyze(doc)
    run.record_finding(result)
    run.update_progress(completed=run.progress.completed + 1)

# Checkpoint semantic state
run.checkpoint()

# Record external side effects (idempotent)
run.record_action(type="github.create_issue", arguments={"title": "...", "body": "..."})

# Complete
run.complete()
```

### 💥 Process Crashes

```bash
continuum resume run_4821
```

```
CONTINUUM RECOVERY

Run: run_4821

Checkpoint:
  v17

State validation:
  ✓ Goal
  ✓ Progress — 3,421 documents already processed
  ✓ 127 findings preserved
  ✓ 14 decisions preserved
  ⚠ Dataset version changed (v3 → v4)
  ✓ Action ledger — no duplicate side effects

Recovery decision:
  REPAIR_AND_RESUME

Repair:
  Revalidate experiments 14–17

Next permitted action:
  dataset_revalidation
```

**Zero duplicated work. Zero duplicated side effects. Verified safe recovery.**

---

## Core Concepts

### 🧠 Semantic Checkpoints

Not a conversation dump. Not a full state snapshot. A **compact, inspectable, versioned** representation of what actually matters:

```json
{
  "run_id": "run_4821",
  "goal": {
    "description": "Analyze 10,000 documents for evidence supporting hypothesis X",
    "version": 3
  },
  "progress": {
    "completed": 3421,
    "pending": 6579,
    "failed": 3
  },
  "decisions": [
    {
      "decision": "Only include peer-reviewed studies",
      "reason": "User requirement",
      "evidence": ["user_instruction_001"],
      "status": "valid"
    }
  ],
  "findings": [
    {
      "id": "finding_17",
      "claim": "Strong correlation observed in dataset subset A",
      "evidence": ["paper_128"],
      "confidence": 0.91
    }
  ],
  "pending_work": [
    "Search 2019-2022 literature",
    "Resolve contradictory evidence"
  ],
  "external_dependencies": [
    { "resource": "dataset", "version": "v3" }
  ]
}
```

### 🔍 State Validation

CONTINUUM **never** blindly trusts an old checkpoint. Before recovery, every component is independently verified:

```
CHECKPOINT
     │
     ▼
STATE VALIDATOR
     │
     ├── environment unchanged?
     ├── dependencies unchanged?
     ├── permissions unchanged?
     ├── external actions still valid?
     ├── evidence still available?
     ├── goals still valid?
     └── previous decisions still valid?
             │
             ▼
       VALID / STALE / CONFLICT
```

Every semantic state component carries a status:

| Component    | Status       |
|:------------|:------------|
| Goal         | `VALID`      |
| Progress     | `VALID`      |
| Decision #12 | `STALE`      |
| Evidence #81 | `VALID`      |
| Dataset      | `CONFLICTED` |
| Approval     | `EXPIRED`    |

### 📒 Idempotent Action Ledger

External side effects are tracked. If the agent crashes after creating GitHub issue #481, CONTINUUM prevents re-creation on recovery:

```
Agent:     Create GitHub issue.
CONTINUUM: Action already completed. External ID: #481. Returning previous result.
```

Action states: `PLANNED` → `STARTED` → `COMPLETED` / `FAILED` / `UNKNOWN` / `COMPENSATED` / `REQUIRES_REVIEW`

If a side effect's outcome is uncertain, CONTINUUM raises `UNKNOWN_SIDE_EFFECT` instead of silently retrying.

### 🔄 Recovery Modes

| Mode               | When                            |
|:-------------------|:-------------------------------|
| `RESUME`           | Checkpoint fully valid          |
| `REPAIR_AND_RESUME`| Checkpoint partially stale      |
| `ROLLBACK`         | Critical state corrupted        |
| `WAIT`             | Dependency temporarily unavailable |
| `REQUEST_HUMAN`    | Side effect outcome uncertain   |
| `ABORT`            | Unrecoverable conflict          |

### 📝 Recovery Contract

Before allowing resume, CONTINUUM generates a deterministic, machine-readable contract:

```json
{
  "run_id": "run_4821",
  "recovery_status": "SAFE_TO_RESUME",
  "verified": ["goal", "completed_documents", "evidence"],
  "invalidated": ["dataset_v3"],
  "required_actions": ["revalidate experiment results"],
  "next_allowed_action": "revalidate_dataset"
}
```

---

## API Reference

### Python SDK

```python
from continuum import Continuum

# Start
runtime = Continuum(storage="sqlite:///agent.db")
run = runtime.start(goal="Analyze these documents")

# Checkpoint
run.checkpoint()

# Record external actions
run.record_action(type="github.create_issue", arguments={...})

# Complete
run.complete()

# Resume after crash
run = runtime.resume("run_4821")
status = run.validate()

if status.safe:
    run.continue_execution()
```

### CLI

```bash
continuum init                              # Initialize storage
continuum run                               # Start a new run
continuum checkpoint                        # Create semantic checkpoint
continuum resume <run_id>                   # Resume from checkpoint
continuum inspect <run_id> --version 17     # Inspect state at version
continuum diff checkpoint_a checkpoint_b    # Diff two checkpoints
continuum validate <run_id>                 # Validate current state
continuum history <run_id>                  # View state version history
continuum replay <run_id>                   # Replay event log
continuum benchmark                         # Run CONTINUUM-Bench suite
```

### State Diff

```bash
continuum diff checkpoint_a checkpoint_b
```

```diff
+ New finding: finding_81
~ Dataset version: v3 → v4
- Decision #7 invalidated
+ Pending task: re-run experiment
```

---

## Architecture

### Data Model (Phase 1 — ✅ Complete)

The foundation is built on **immutable, frozen Pydantic v2 models** with cryptographic hash chains:

```
SemanticState
├── Goal              # What the agent is trying to do
├── Progress          # How far along (completed / pending / failed)
├── PlanStep[]        # Structured execution plan
├── Decision[]        # Durable decisions with evidence trails
├── Finding[]         # Claims with evidence and confidence scores
├── Evidence[]        # Referenced evidence with checksums
├── PendingWork[]     # Remaining tasks
├── Approval[]        # Human approvals with expiration
├── ExternalDependency[]  # Versioned external resources
└── ModelState        # Model-specific assumptions (revalidated on switch)
```

### Event Log

Append-only, hash-chained event stream — the **source of truth** for every run:

```
e1.prev_hash = None          e1.hash = H(content(e1))
e2.prev_hash = e1.hash       e2.hash = H(content(e2))
e3.prev_hash = e2.hash       e3.hash = H(content(e3))
```

Tamper detection is built in. `EventLog.verify()` recomputes every digest and re-walks the chain, localizing any damage.

**18 event types**: `RUN_STARTED`, `TOOL_CALLED`, `DECISION_CREATED`, `STATE_CHECKPOINTED`, `ENVIRONMENT_CHANGED`, `RECOVERY_STARTED`, `ACTION_RECONCILED`, and more.

### Security

- **Deterministic canonical hashing** — sorted keys, UTC-normalized timestamps, enum-by-value serialization, rejection of non-finite floats
- **Hash-chained events** — tamper-evident audit trail
- **Credentials never serialized** into state — referenced, never stored
- **Provenance tracking** — every state component traces back to its origin event

---

## Project Structure

```
continuum/
├── README.md
├── LICENSE                          # Apache 2.0
├── CHANGELOG.md
├── pyproject.toml
│
├── src/
│   └── continuum/
│       ├── __init__.py              # Public API surface
│       ├── models.py                # Immutable data models (570 LOC)
│       ├── events.py                # Hash-chained event log (309 LOC)
│       └── security/
│           ├── __init__.py
│           └── hashing.py           # Deterministic canonical hashing
│
└── tests/
    ├── test_models.py               # Model invariants & serialization
    ├── test_events.py               # Chain integrity & tamper detection
    └── test_hashing.py              # Canonical hashing properties
```

---

## Research: CONTINUUM-Bench

CONTINUUM includes a benchmark suite for evaluating long-running agent recovery under controlled failures.

### Scenarios

| Scenario             | Description                           |
|:---------------------|:-------------------------------------|
| Process crash        | Mid-task termination                  |
| Context compaction   | Context window overflow               |
| Tool failure         | External tool becomes unavailable     |
| API timeout          | Session expires mid-task              |
| Dataset change       | External data version changes         |
| File modification    | Working files modified externally     |
| Permission change    | Access revoked during execution       |
| Model switch         | LLM provider changes mid-task        |
| Stale decision       | Previously valid decision invalidated |
| Partial completion   | Task partially finished before crash  |

### Key Metrics

| Metric                      | Definition                                                |
|:----------------------------|:---------------------------------------------------------|
| **Recovery Fidelity**       | `correct_recovered_decisions / required_recovered_decisions` |
| **Recovery Compression**    | `full_context_tokens / semantic_recovery_tokens`          |
| **Duplicate Work Ratio**    | Previously completed work repeated after recovery         |
| **Duplicate Side Effects**  | External actions accidentally repeated                    |
| **Recovery Latency**        | Time from crash to safe continuation                      |
| **State Validation Accuracy** | Proportion of stale states correctly detected           |

> **Note**: No benchmark results are claimed yet. The harness is being built. Results will be published only after experimental measurement.

---

## Roadmap

| Phase | Component                         | Status          |
|:-----:|:----------------------------------|:---------------|
|   1   | Data models + Event system        | ✅ Complete     |
|   2   | Semantic state representation     | 🔧 In Progress |
|   3   | SQLite persistence                | ⬜ Planned     |
|   4   | Checkpoint creation               | ⬜ Planned     |
|   5   | State validation                  | ⬜ Planned     |
|   6   | Action ledger + Idempotency       | ⬜ Planned     |
|   7   | Recovery engine                   | ⬜ Planned     |
|   8   | CLI                               | ⬜ Planned     |
|   9   | Crash recovery examples           | ⬜ Planned     |
|  10   | Environment snapshots & diffs     | ⬜ Planned     |
|  11   | Framework adapters                | ⬜ Planned     |
|  12   | Benchmark suite                   | ⬜ Planned     |
|  13   | Cloud API (FastAPI + PostgreSQL)  | ⬜ Planned     |
|  14   | Dashboard                         | ⬜ Planned     |

### Framework Adapters (Planned)

- Generic Python agent
- OpenAI Agents SDK
- LangGraph

---

## What CONTINUUM Is Not

| ❌ Not This              | ✅ This Instead                                        |
|:------------------------|:------------------------------------------------------|
| An LLM                  | A reliability layer for agents that use LLMs           |
| An agent framework      | A recovery layer that plugs into any framework         |
| A vector database       | Structured semantic state, not embeddings              |
| A RAG system            | Verified checkpoints, not retrieval-augmented memory   |
| A workflow engine       | A recovery layer, not an orchestrator                  |

**The core abstraction:**

```
semantic state  +  environment validation  +  action reconciliation  =  safe recovery
```

---

## Development

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

```bash
git clone https://github.com/Cyrax321/CONTINUUM.git
cd CONTINUUM
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest                    # Run all tests
pytest --cov              # With coverage
pytest -x -v              # Verbose, stop on first failure
```

### Code Quality

```bash
ruff check src/ tests/    # Linting
ruff format src/ tests/   # Formatting
mypy                      # Type checking
```

---

## Contributing

Contributions are welcome. The project is in early development (Phase 1 complete) and there are many components to build.

**Good starting points:**
- Storage engine (SQLite backend)
- State extraction and validation
- Framework adapters
- Benchmark scenarios
- Documentation

Please open an issue before submitting large PRs to discuss the approach.

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <sub>Built with the conviction that agent work should survive the agent.</sub>
</p>
