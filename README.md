<p align="center">
  <img src="docs/assets/logo.png" alt="CONTINUUM Logo" width="480" />
</p>

<p align="center">
  <strong>Agents that can lose their context without losing their work.</strong>
</p>

<p align="center">
  A lightweight, framework-agnostic semantic recovery layer for long-running AI agents.
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue?style=flat-square" alt="License" /></a>
  <a href="https://pydantic.dev"><img src="https://img.shields.io/badge/pydantic-v2-E92063?style=flat-square&logo=pydantic&logoColor=white" alt="Pydantic v2" /></a>
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

CONTINUUM investigates a narrower, harder question:

> Can an agent resume safely from a compact semantic representation of its task state, while independently verifying whether that state is still valid in the current environment?

This is not a generic agent framework. Not a memory system. Not a workflow engine.

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

```bash
pip install continuum-agent
```

```python
from continuum import Continuum

runtime = Continuum("agent.db")

run = runtime.start(goal="Analyze 10,000 documents for evidence supporting hypothesis X")

for doc in documents:
    result = analyze(doc)
    run.record_finding(result)
    run.update_progress(completed=run.progress.completed + 1)

run.checkpoint()
run.record_action(type="github.create_issue", arguments={"title": "...", "body": "..."})
run.complete()
```

Process crashes. Restart:

```bash
continuum resume run_4821
```

```
CONTINUUM RECOVERY

Run: run_4821
Checkpoint: v17

State validation:
  [ok] Goal
  [ok] Progress — 3,421 documents already processed
  [ok] 127 findings preserved
  [ok] 14 decisions preserved
  [!!] Dataset version changed (v3 -> v4)
  [ok] Action ledger — no duplicate side effects

Recovery decision: REPAIR_AND_RESUME
Repair: Revalidate experiments 14-17
Next permitted action: dataset_revalidation
```

Zero duplicated work. Zero duplicated side effects. Verified safe recovery.

---

## Core Concepts

### Semantic Checkpoints

Not a conversation dump. Not a full state snapshot. A compact, inspectable, versioned representation of what the agent actually needs to continue:

```json
{
  "run_id": "run_4821",
  "goal": {
    "description": "Analyze 10,000 documents for evidence supporting hypothesis X",
    "version": 3
  },
  "progress": { "completed": 3421, "pending": 6579, "failed": 3 },
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

### State Validation

CONTINUUM never blindly trusts an old checkpoint. Before recovery, every component is independently verified:

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

| Component    | Status       |
|:------------|:------------|
| Goal         | `VALID`      |
| Progress     | `VALID`      |
| Decision #12 | `STALE`      |
| Evidence #81 | `VALID`      |
| Dataset      | `CONFLICTED` |
| Approval     | `EXPIRED`    |

### Idempotent Action Ledger

External side effects are tracked. If the agent crashes after creating GitHub issue #481, CONTINUUM prevents re-creation on recovery:

```
Agent:     Create GitHub issue.
CONTINUUM: Action already completed. External ID: #481. Returning previous result.
```

Action states: `PLANNED` > `STARTED` > `COMPLETED` / `FAILED` / `UNKNOWN` / `COMPENSATED` / `REQUIRES_REVIEW`

If the outcome of a side effect is uncertain, CONTINUUM raises `UNKNOWN_SIDE_EFFECT` instead of silently retrying.

### Recovery Modes

| Mode               | Trigger                           |
|:-------------------|:----------------------------------|
| `RESUME`           | Checkpoint fully valid            |
| `REPAIR_AND_RESUME`| Checkpoint partially stale        |
| `ROLLBACK`         | Critical state corrupted          |
| `WAIT`             | Dependency temporarily unavailable|
| `REQUEST_HUMAN`    | Side effect outcome uncertain     |
| `ABORT`            | Unrecoverable conflict            |

### Recovery Contract

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

## API

### Python

```python
from continuum import Continuum

runtime = Continuum(storage="sqlite:///agent.db")
run = runtime.start(goal="Analyze these documents")

run.checkpoint()
run.record_action(type="github.create_issue", arguments={...})
run.complete()

# After crash
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
continuum benchmark                         # Run benchmark suite
```

### State Diff

```bash
continuum diff checkpoint_a checkpoint_b
```

```diff
+ New finding: finding_81
~ Dataset version: v3 -> v4
- Decision #7 invalidated
+ Pending task: re-run experiment
```

---

## Architecture

### Data Model (Phase 1 — Complete)

Built on immutable, frozen Pydantic v2 models with cryptographic hash chains:

```
SemanticState
+-- Goal                    What the agent is trying to do
+-- Progress                Completed / pending / failed counts
+-- PlanStep[]              Structured execution plan
+-- Decision[]              Durable decisions with evidence trails
+-- Finding[]               Claims with evidence and confidence scores
+-- Evidence[]              Referenced evidence with checksums
+-- PendingWork[]           Remaining tasks
+-- Approval[]              Human approvals with expiration
+-- ExternalDependency[]    Versioned external resources
+-- ModelState              Model-specific assumptions (revalidated on switch)
```

### Event Log

Append-only, hash-chained event stream. Source of truth for every run:

```
e1.prev_hash = None          e1.hash = H(content(e1))
e2.prev_hash = e1.hash       e2.hash = H(content(e2))
e3.prev_hash = e2.hash       e3.hash = H(content(e3))
```

Tamper detection built in. `EventLog.verify()` recomputes every digest and re-walks the chain, localizing damage.

18 event types covering the full lifecycle: `RUN_STARTED`, `TOOL_CALLED`, `DECISION_CREATED`, `STATE_CHECKPOINTED`, `ENVIRONMENT_CHANGED`, `RECOVERY_STARTED`, `ACTION_RECONCILED`, and more.

### Security

- **Deterministic canonical hashing** — sorted keys, UTC-normalized timestamps, enum-by-value serialization, rejection of non-finite floats
- **Hash-chained events** — tamper-evident audit trail
- **Credentials never serialized** into state — referenced only, never stored
- **Provenance tracking** — every state component traces back to its origin event

---

## Project Structure

```
continuum/
+-- README.md
+-- LICENSE                          Apache 2.0
+-- CHANGELOG.md
+-- pyproject.toml
|
+-- src/
|   +-- continuum/
|       +-- __init__.py              Public API surface
|       +-- models.py                Immutable data models (570 LOC)
|       +-- events.py                Hash-chained event log (309 LOC)
|       +-- security/
|           +-- __init__.py
|           +-- hashing.py           Deterministic canonical hashing
|
+-- tests/
    +-- test_models.py               Model invariants and serialization
    +-- test_events.py               Chain integrity and tamper detection
    +-- test_hashing.py              Canonical hashing properties
```

---

## CONTINUUM-Bench

Benchmark suite for evaluating long-running agent recovery under controlled failures.

### Scenarios

| Scenario             | Description                           |
|:---------------------|:--------------------------------------|
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

### Metrics

| Metric                       | Definition                                                     |
|:-----------------------------|:---------------------------------------------------------------|
| Recovery Fidelity            | `correct_recovered_decisions / required_recovered_decisions`    |
| Recovery Compression         | `full_context_tokens / semantic_recovery_tokens`               |
| Duplicate Work Ratio         | Previously completed work repeated after recovery              |
| Duplicate Side Effects       | External actions accidentally repeated                         |
| Recovery Latency             | Time from crash to safe continuation                           |
| State Validation Accuracy    | Proportion of stale states correctly detected                  |

No benchmark results are claimed. The harness is being built. Results will be published after experimental measurement.

---

## Roadmap

| Phase | Component                         | Status      |
|:-----:|:----------------------------------|:------------|
|   1   | Data models + Event system        | Complete    |
|   2   | Semantic state representation     | In progress |
|   3   | SQLite persistence                | Planned     |
|   4   | Checkpoint creation               | Planned     |
|   5   | State validation                  | Planned     |
|   6   | Action ledger + Idempotency       | Planned     |
|   7   | Recovery engine                   | Planned     |
|   8   | CLI                               | Planned     |
|   9   | Crash recovery examples           | Planned     |
|  10   | Environment snapshots and diffs   | Planned     |
|  11   | Framework adapters                | Planned     |
|  12   | Benchmark suite                   | Planned     |
|  13   | Cloud API (FastAPI + PostgreSQL)  | Planned     |
|  14   | Dashboard                         | Planned     |

Planned framework adapters: generic Python agent, OpenAI Agents SDK, LangGraph.

---

## What CONTINUUM Is Not

| Not this              | This instead                                           |
|:----------------------|:-------------------------------------------------------|
| An LLM                | A reliability layer for agents that use LLMs           |
| An agent framework    | A recovery layer that plugs into any framework         |
| A vector database     | Structured semantic state, not embeddings              |
| A RAG system          | Verified checkpoints, not retrieval-augmented memory   |
| A workflow engine     | A recovery layer, not an orchestrator                  |

The core abstraction:

```
semantic state  +  environment validation  +  action reconciliation  =  safe recovery
```

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

## Contributing

The project is in early development (Phase 1 complete). There are many components to build — storage engines, state validation, framework adapters, benchmark scenarios, documentation.

Open an issue before submitting large PRs.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
