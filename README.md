<p align="center">
  <img src="docs/assets/continuum-mark.png" alt="CONTINUUM Logo" width="160" />
</p>

<h1 align="center">CONTINUUM</h1>

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
  <a href="https://cyrax321.github.io/CONTINUUM/"><img src="https://img.shields.io/badge/website-live_demo-E06D53?style=flat-square" alt="Website Demo" /></a>
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

> Not published to PyPI yet. Install from a clone: `uv venv && uv pip install -e ".[dev]"`

What runs today (Phases 1–5): record events, project state, checkpoint, survive a crash, and refuse to resume on stale state.

```python
from continuum import EventType, Run, SQLiteStorage, project

store = SQLiteStorage("agent.db")
store.create_run(Run(run_id="run_4821", goal="Analyze 10,000 documents"))
store.append_event(
    "run_4821", EventType.RUN_STARTED, {"goal": "Analyze 10,000 documents", "total": 10_000}
)

for i, doc in enumerate(documents):
    analyze(doc)
    store.append_event("run_4821", EventType.WORK_COMPLETED, {"doc": i})
```

The process dies. A new one picks up exactly where it stopped:

```python
store = SQLiteStorage("agent.db")
state = project("run_4821", store.read_events("run_4821"))

print(state.progress.completed)  # 3421 — already done, not repeated
print(store.verify_events("run_4821").ok)  # True — chain intact after the crash

for i, doc in enumerate(documents[state.progress.completed :], state.progress.completed):
    ...
```

### The API this is being built toward

The ergonomic wrapper below is **not implemented yet** — it arrives with the runtime and CLI in
Phases 4–8. It is shown so the direction is clear, not because it works today:

```python
from continuum import Continuum  # not available yet

runtime = Continuum("agent.db")
run = runtime.start(goal="Analyze 10,000 documents")
run.checkpoint()
run.record_action(type="github.create_issue", arguments={...})
run.complete()
```

```bash
continuum resume run_4821                # CLI: Phase 8
```

Target output, illustrating the intended recovery report (not a recording of a working build):

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

The goal: zero duplicated work, zero duplicated side effects, verified safe recovery. Crash recovery
with zero duplicated work is [demonstrated below](#durable-storage-phase-3--complete) against the
storage layer that exists today; side-effect deduplication needs the action ledger in Phase 6.

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

### Python — available now

```python
from continuum import EventType, Run, SQLiteStorage, VersionChain, diff_states, project

store = SQLiteStorage("sqlite:///agent.db")
store.create_run(Run(run_id="run_4821", goal="Analyze these documents"))
store.append_event("run_4821", EventType.RUN_STARTED, {"goal": "...", "total": 100})

state = project("run_4821", store.read_events("run_4821"))  # fold events into state
store.put_version(state, reason="milestone")  # versioned history
store.verify_events("run_4821")  # audit the chain
diff_states(previous, state)  # what changed, semantically
```

### Python — planned (Phases 4–7)

```python
from continuum import Continuum  # not implemented yet

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

### CLI — planned (Phase 8)

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

29 event types covering the full lifecycle: `RUN_STARTED`, `TOOL_CALLED`, `DECISION_CREATED`, `STATE_CHECKPOINTED`, `ENVIRONMENT_CHANGED`, `RECOVERY_STARTED`, `ACTION_RECONCILED`, and more.

### Semantic State Projection (Phase 2 — Complete)

State is not stored and mutated. It is *projected* from the event log by a pure fold:

```
state = reduce(apply, events, empty_state)
```

Two properties make this safe to recover from, and both are tested:

- **Reproducibility** — folding the same prefix twice yields an equal state. Timestamps come from the events, never from `now()`.
- **Prefix-closure** — `project(events, upto=n)` equals the state that existed after event `n`.

Together with the log's `trusted_through`, a run whose tail was tampered with can still be recovered up to its last verified event:

```python
report = log.verify("run_4821")
trusted = report.trusted_through["run_4821"]
state = project("run_4821", log.events("run_4821"), upto=trusted)
```

Unknown event types are counted, not fatal — a newer writer's vocabulary must never render a run unrecoverable.

### State Extraction

Extraction is pluggable through a single protocol:

```python
class StateExtractor(Protocol):
    name: str

    def extract(self, context: ExtractionContext) -> SemanticState: ...
```

`DeterministicExtractor` is the default and the only one required. It folds the event log — no model, no network, no clock.

`LLMExtractor` is optional and deliberately constrained. The caller supplies the callable; CONTINUUM has no provider dependency, no API key handling, no network default. The model may only **add** components, never modify or delete recorded facts. Everything it produces is tagged `Origin.LLM` and forced to `REQUIRES_REVIEW`. If it raises, extraction degrades to the deterministic result — losing an optional enrichment must never cost a recovery.

The deterministic layer is authoritative. The model is an advisor.

### State Versioning

Every accepted mutation appends a version. Versions are content-addressed and linked, so history can be audited exactly like the event log:

```python
chain = VersionChain("run_4821")
chain.commit(state, reason="milestone")  # -> VersionEntry(version=0)
chain.commit(state, reason="timer")  # -> None: semantically unchanged
chain.verify()  # recompute fingerprints, re-walk links
```

`commit` returns `None` when nothing meaningful changed, so timer-driven checkpoint policies cannot inflate history with noise. Fingerprints ignore bookkeeping fields — a state means the same thing regardless of when it was projected.

### Durable Storage (Phase 3 — Complete)

SQLite by default. No server, no cloud account, no daemon:

```python
from continuum import SQLiteStorage, Run, EventType, project

with SQLiteStorage("agent.db") as store:
    store.create_run(Run(run_id="run_4821", goal="Analyze 10,000 documents"))
    store.append_event("run_4821", EventType.RUN_STARTED, {"goal": "...", "total": 10000})
    store.append_event("run_4821", EventType.WORK_COMPLETED, {"count": 3421})

    state = project("run_4821", store.read_events("run_4821"))
    store.verify_events("run_4821").ok
```

**What the engine guarantees:** append-only events, atomic sequence allocation, and durability once `append_event` returns. WAL journaling keeps readers unblocked while the agent writes. `synchronous=FULL` costs an fsync per append — the alternative can lose the last commits on a crash, silently reintroducing exactly the duplicate-work problem CONTINUUM exists to prevent.

**What it does not guarantee:** exactly-once semantics. A crash between an external side effect and its ledger write leaves the ledger behind reality. Storage cannot close that gap alone; the action ledger reconciles it in Phase 6. The engine is also single-host and not encrypted at rest.

**Write races fail loudly.** Two writers appending to one run take an `IMMEDIATE` lock, with `UNIQUE(run_id, sequence)` as a backstop. One commits, the other gets a `ConcurrentWriteError`. A silently forked chain that still verifies clean would be the worst possible failure, because it looks correct.

**Corruption is refused, never returned.** Runs, versions and checkpoints are validated and hash-checked on read; a mismatch raises `CorruptedRecord` rather than handing back state an agent might act on.

Verified end to end — a worker killed with `os._exit(9)` mid-run, then restarted against the same file:

```text
[pid 58807] started at 0 completed
[pid 58807] *** CRASH at doc 39 ***

[pid 58808] resumed at 40 completed
[pid 58808] finished at 100 completed

events        102, integrity ok=True, trusted_through=102
docs written  100 events, 100 unique -> duplicates=0
```

### Checkpointing (Phase 4 — Complete)

Checkpointing every turn is the obvious design and the wrong one: it costs an fsync per step and fills history with versions that mean nothing. A policy decides instead.

```python
from continuum import CheckpointManager, SemanticPolicy, SQLiteStorage

manager = CheckpointManager(store, policy=SemanticPolicy(progress_stride=25))

for doc in documents:
    process(doc)
    manager.maybe_checkpoint("run_4821")  # writes only when it matters
```

| Policy | Fires when |
|:--|:--|
| `ManualPolicy` | asked explicitly |
| `IntervalPolicy` | N seconds since the last checkpoint |
| `EventPolicy` | a side effect or milestone event occurs |
| `SemanticPolicy` | the *meaning* of the state changed |
| `ContextPressurePolicy` | the context window is filling up |
| `HybridPolicy` | any of the above (the default) |

`SemanticPolicy` is the interesting one. Grinding from document 3,400 to 3,401 changes progress but nothing structural. Invalidating a single decision changes what the agent may safely do next. The first is ignored; the second always checkpoints.

Policies are pure functions of an explicit context — including the clock — so checkpoint timing is testable rather than a source of flaky tests.

**Restore replays the gap.** A checkpoint plus the events recorded after it, so a crash *between* checkpoints does not discard the work in between:

```python
restored = manager.restore("run_4821")
restored.state.progress.completed  # caught up to the log
restored.pending_events  # how much was replayed
```

Measured on a 200-document run killed at document 117:

```text
*** CRASH at doc 117 ***

restored from checkpoint v8 | replayed 17 events (not 135)
finished at 200
```

### Recovery Context

On resume the agent is handed the minimum sufficient briefing, not the transcript:

```text
CURRENT GOAL
  Analyze 200 documents  (goal v1)

NEXT SAFE ACTION
  continue_analysis

VERIFIED PROGRESS
  200 completed, 0 pending, 0 failed (of 200)
  derived from events 1..227

VALID DECISIONS
  d_12: Only peer-reviewed studies

RELEVANT FINDINGS
  f_0 (0.90): pattern at 0
  ... and 5 more findings

EXTERNAL DEPENDENCIES
  dataset: v3 [valid]
```

That is a 228-event run rendered in 410 characters. **Stale state is shown, never hidden** — an agent that is not told its dataset changed will confidently continue on invalid assumptions. Under a token budget, sections drop from the least important end, but goal, verified progress and stale state are never sacrificed.

Token figures reported by `estimate_tokens` are a **character-based heuristic, not a tokenizer**. CONTINUUM takes no model-provider dependency for a size hint. No compression ratio is claimed until the benchmark measures real tokens.

### State Validation (Phase 5 — Complete)

**A persisted checkpoint is not trustworthy merely because it was persisted.** Before an agent resumes, every component is checked against the environment as it is now.

```python
from continuum import StaticProvider, capture_environment, validate_state

now = capture_environment("run_4821", StaticProvider(dataset="v4"))
outcome = validate_state(
    restored.state,
    checkpoint_environment=restored.checkpoint.environment,
    current_environment=now,
)

outcome.safe  # False
outcome.state  # same state, with statuses already revised
```

**Staleness propagates.** A dataset moving v3 to v4 does not only invalidate the dependency — it invalidates the reasoning built on it. The validator walks `dependency -> evidence -> finding -> decision`:

```text
[!!] external dependency dataset: conflicted — v3 -> v4
[!!] evidence paper_128: stale — source 'dataset' changed
[!!] finding finding_17: stale — rests on changed evidence: paper_128
[!!] decision d_12: stale — rests on changed support: finding_17
[ok] goal: valid — v1
[ok] progress: valid — 60 completed

Safe to resume: no
```

Marking only the dependency would leave the agent reasoning from conclusions it can no longer justify. State that did not depend on the change is left untouched, so the report stays worth reading.

With the same dataset still in place, the identical run resumes cleanly:

```text
[ok] external dependency dataset: valid — verified unchanged
Safe to resume: yes
```

**Uncertainty degrades, it does not resolve.** A resource that could not be inspected — an API that timed out, a file now unreadable — becomes `UNKNOWN`, never `VALID`. `UNKNOWN` is enough to withhold a clean resume. The system may say "I cannot tell"; it may not guess in its own favour. Callers who genuinely tolerate uncertainty opt in with `strict_unknown=False`, and it stays visible in the report.

**Model switches are never assumed safe.** State produced under one model that carries model-specific assumptions is marked `STALE` when another model takes over, and requires revalidation.

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
|       +-- models.py                Immutable data models
|       +-- events.py                Hash-chained event log
|       +-- state/
|       |   +-- __init__.py
|       |   +-- semantic.py          Deterministic event -> state projection
|       |   +-- extractor.py         Pluggable extraction (LLM optional)
|       |   +-- versioning.py        Content-addressed version chain
|       |   +-- diff.py              Semantic diff and renderer
|       |   +-- validator.py         Validation and staleness propagation
|       +-- storage/
|       |   +-- __init__.py          open_storage() URL dispatch
|       |   +-- base.py              Storage interface and stated guarantees
|       |   +-- sqlite.py            WAL, transactions, integrity on read
|       +-- checkpoint/
|       |   +-- __init__.py
|       |   +-- policy.py            When to checkpoint
|       |   +-- manager.py           Create, seal, persist, restore
|       |   +-- context.py           Bounded recovery context
|       +-- environment/
|       |   +-- __init__.py
|       |   +-- snapshot.py          Pluggable environment capture
|       |   +-- diff.py              Conservative snapshot comparison
|       +-- security/
|           +-- __init__.py
|           +-- hashing.py           Deterministic canonical hashing
|
+-- tests/
    +-- test_models.py               Model invariants and serialization
    +-- test_events.py               Chain integrity and tamper detection
    +-- test_hashing.py              Canonical hashing properties
    +-- test_projection.py           Fold correctness, reproducibility, prefix-closure
    +-- test_projection_edges.py     Malformed logs and partial payloads
    +-- test_extractor.py            Extractor protocol and LLM containment
    +-- test_versioning.py           Version chain integrity
    +-- test_diff.py                 Semantic diff behaviour
    +-- test_storage.py              Persistence, durability, corruption refusal
    +-- test_storage_concurrency.py  Thread and multi-process write races
    +-- test_storage_edges.py        Payload validation and URL handling
    +-- test_checkpoint_policy.py    Policy decisions and triggers
    +-- test_checkpoint_manager.py   Creation, restore, crash interleavings
    +-- test_recovery_context.py     Bounded context and truncation safety
    +-- test_environment.py          Capture, diffing, unverifiable resources
    +-- test_validator.py            Validation and staleness propagation
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
|   2   | Semantic state representation     | Complete    |
|   3   | SQLite persistence                | Complete    |
|   4   | Checkpoint creation               | Complete    |
|   5   | State validation                  | Complete    |
|   6   | Action ledger + Idempotency       | Planned     |
|   7   | Recovery engine                   | Planned     |
|   8   | CLI                               | Planned     |
|   9   | Crash recovery examples           | Planned     |
|  10   | Environment snapshots and diffs   | Complete    |
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

The project is in early development (Phases 1–5 and 10 complete). There are many components to build — storage engines, state validation, framework adapters, benchmark scenarios, documentation.

Open an issue before submitting large PRs.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
