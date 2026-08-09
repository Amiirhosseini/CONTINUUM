# CONTINUUM

**Verifiable semantic recovery layer for long-running AI agents.**

Agents that can lose their context without losing their work.

---

## Overview

CONTINUUM is a lightweight, framework-agnostic infrastructure layer that externalizes the minimum verified task state needed to survive crashes, context loss, and environmental changes.

Modern AI agents perform long-running tasks involving many LLM calls, tool invocations, external APIs, files, databases, and human approvals. When they fail — process crash, deployment replacement, context compaction, API expiration, environment mutation — the typical response is to replay the entire task. That causes duplicated work, duplicated API calls, duplicated side effects, higher cost, lost decisions, and inconsistent state.

CONTINUUM investigates a narrower problem:

> Can an agent resume safely from a compact semantic representation of its task state, while independently verifying whether that state is still valid in the current environment?

It is not an agent framework, a memory system, a vector database, or a workflow engine. It is a reliability layer.

---

## Architecture

CONTINUUM separates LLM context (temporary) from durable task state (permanent).

```
                   AI AGENT
                      |
                      v
              +---------------+
              | CONTINUUM SDK |
              +-------+-------+
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

The core abstraction:

```
semantic state  +  environment validation  +  action reconciliation  =  safe recovery
```

---

## Quick Start

```
pip install continuum-agent
```

```python
from continuum import Continuum

runtime = Continuum("agent.db")

run = runtime.start(goal="Analyze 10,000 documents")

# ... process items, record findings, make decisions ...

run.checkpoint()

run.record_action(type="github.create_issue", arguments={"title": "...", "body": "..."})

run.complete()
```

Recovery after crash:

```
continuum resume run_4821
```

```
CONTINUUM RECOVERY

Run: run_4821
Checkpoint: v17

State validation:
  [ok] Goal
  [ok] Progress (3,421 documents already processed)
  [ok] 127 findings preserved
  [ok] 14 decisions preserved
  [!!] Dataset version changed (v3 -> v4)
  [ok] Action ledger (no duplicate side effects)

Recovery decision: REPAIR_AND_RESUME
Repair: Revalidate experiments 14-17
Next permitted action: dataset_revalidation
```

Zero duplicated work. Zero duplicated side effects. Verified safe recovery.

---

## Semantic Checkpoints

CONTINUUM does not save conversation history. It does not save full agent state. It constructs a compact, inspectable, versioned semantic checkpoint — the minimum verified information required to continue the task.

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

Properties: compact, inspectable, versioned, deterministic where possible, independently verifiable, diffable, recoverable, serializable.

---

## State Validation

CONTINUUM never blindly trusts an old checkpoint. Before recovery, every component is independently verified against the current environment:

```
CHECKPOINT
     |
     v
STATE VALIDATOR
     |
     +-- environment unchanged?
     +-- dependencies unchanged?
     +-- permissions unchanged?
     +-- external actions still valid?
     +-- evidence still available?
     +-- goals still valid?
     +-- previous decisions still valid?
             |
             v
       VALID / STALE / CONFLICT
```

Every semantic state component carries a status:

```
Goal             VALID
Progress         VALID
Decision #12     STALE
Evidence #81     VALID
Dataset          CONFLICTED
Approval         EXPIRED
```

This is exposed through the API.

---

## Action Ledger

The system maintains an idempotent action ledger for external side effects. If the agent crashes after creating GitHub issue #481, recovery does not re-create it:

```
Agent:      Create GitHub issue.
CONTINUUM:  Action already completed. External ID: #481. Returning previous result.
```

Action states: `PLANNED`, `STARTED`, `COMPLETED`, `FAILED`, `UNKNOWN`, `COMPENSATED`, `REQUIRES_REVIEW`.

If the system cannot determine whether an external side effect occurred, it returns `UNKNOWN_SIDE_EFFECT` and requires a reconciliation strategy. It does not blindly retry.

---

## Recovery Modes

```
Checkpoint valid                  -> RESUME
Checkpoint partially stale        -> REPAIR_AND_RESUME
Critical state corrupted          -> ROLLBACK
Dependency temporarily unavailable -> WAIT
Side effect outcome uncertain     -> REQUEST_HUMAN
Unrecoverable conflict            -> ABORT
```

Before allowing resume, CONTINUUM generates a deterministic, machine-readable recovery contract:

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

## CLI

```
continuum init                              Initialize storage
continuum run                               Start a new run
continuum checkpoint                        Create semantic checkpoint
continuum resume <run_id>                   Resume from checkpoint
continuum inspect <run_id> --version 17     Inspect state at version
continuum diff checkpoint_a checkpoint_b    Diff two checkpoints
continuum validate <run_id>                 Validate current state
continuum history <run_id>                  View state version history
continuum replay <run_id>                   Replay event log
continuum benchmark                         Run benchmark suite
```

---

## Python API

```python
from continuum import Continuum

# Start
runtime = Continuum(storage="sqlite:///agent.db")
run = runtime.start(goal="Analyze these documents")

# Work
run.checkpoint()
run.record_action(type="github.create_issue", arguments={...})
run.complete()

# Resume
run = runtime.resume("run_4821")
status = run.validate()

if status.safe:
    run.continue_execution()
```

---

## Data Model

The foundation is built on immutable, frozen Pydantic v2 models with cryptographic hash chains.

```
SemanticState
  Goal                   What the agent is trying to do
  Progress               Completed / pending / failed counts
  PlanStep[]             Structured execution plan
  Decision[]             Durable decisions with evidence trails
  Finding[]              Claims with evidence and confidence scores
  Evidence[]             Referenced evidence with checksums
  PendingWork[]          Remaining tasks
  Approval[]             Human approvals with expiration
  ExternalDependency[]   Versioned external resources
  ModelState             Model-specific assumptions (revalidated on switch)
```

### Event Log

Append-only, hash-chained event stream. This is the source of truth for every run.

```
e1.prev_hash = None          e1.hash = H(content(e1))
e2.prev_hash = e1.hash       e2.hash = H(content(e2))
e3.prev_hash = e2.hash       e3.hash = H(content(e3))
```

`EventLog.verify()` recomputes every digest and re-walks the chain, localizing any damage. This is tamper evidence, not tamper proofing.

18 event types: `RUN_STARTED`, `TOOL_CALLED`, `DECISION_CREATED`, `STATE_CHECKPOINTED`, `ENVIRONMENT_CHANGED`, `RECOVERY_STARTED`, `ACTION_RECONCILED`, and others.

### Security

- Deterministic canonical hashing with sorted keys, UTC-normalized timestamps, enum-by-value serialization, and explicit rejection of non-finite floats.
- Hash-chained events for tamper-evident audit trails.
- Credentials are never serialized into state. Referenced, never stored.
- Every state component tracks provenance back to its origin event.

---

## Project Structure

```
src/continuum/
    __init__.py              Public API surface
    models.py                Immutable data models
    events.py                Hash-chained event log
    security/
        hashing.py           Deterministic canonical hashing

tests/
    test_models.py           Model invariants and serialization
    test_events.py           Chain integrity and tamper detection
    test_hashing.py          Canonical hashing properties
```

---

## CONTINUUM-Bench

A benchmark suite for evaluating long-running agent recovery under controlled failures.

Scenarios: process crash, context compaction, tool failure, API timeout, dataset change, file modification, permission change, model switch, stale decision, partial completion.

Metrics:

- **Recovery Fidelity** — correct recovered decisions / required recovered decisions.
- **Recovery Compression Ratio** — full context tokens / semantic recovery tokens.
- **Duplicate Work** — previously completed work repeated after recovery.
- **Duplicate Side Effects** — external actions accidentally repeated.
- **Recovery Latency** — time from crash to safe continuation.
- **State Validation Accuracy** — proportion of stale states correctly detected.

No benchmark results are claimed. The harness is being built. Results will be published only after experimental measurement.

---

## Roadmap

```
Phase  1   Data models + Event system             COMPLETE
Phase  2   Semantic state representation           IN PROGRESS
Phase  3   SQLite persistence                      PLANNED
Phase  4   Checkpoint creation                     PLANNED
Phase  5   State validation                        PLANNED
Phase  6   Action ledger + Idempotency             PLANNED
Phase  7   Recovery engine                         PLANNED
Phase  8   CLI                                     PLANNED
Phase  9   Crash recovery examples                 PLANNED
Phase 10   Environment snapshots and diffs         PLANNED
Phase 11   Framework adapters (Generic, OpenAI, LangGraph)   PLANNED
Phase 12   Benchmark suite                         PLANNED
Phase 13   Cloud API (FastAPI + PostgreSQL)         PLANNED
Phase 14   Dashboard                               PLANNED
```

---

## Development

Requirements: Python 3.11+

```
git clone https://github.com/Cyrax321/CONTINUUM.git
cd CONTINUUM
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Tests:

```
pytest
pytest --cov
pytest -x -v
```

Code quality:

```
ruff check src/ tests/
ruff format src/ tests/
mypy
```

---

## Contributing

The project is in early development. Phase 1 (data models, event system, hashing) is complete. There are many components to build.

Useful starting points: storage engine (SQLite backend), state extraction and validation, framework adapters, benchmark scenarios, documentation.

Open an issue before submitting large PRs.

---

## License

Apache License 2.0. See [LICENSE](LICENSE).
