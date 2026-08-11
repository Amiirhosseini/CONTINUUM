<p align="center">
  <img src="docs/assets/readme-img.png" alt="CONTINUUM Banner" width="100%" />
</p>

<p align="center">
  <strong>A lightweight, framework-agnostic semantic recovery layer for long-running AI agents.</strong>
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

CONTINUUM's differentiator is three-part: **semantic checkpointing** (a compact, versioned representation of what the agent actually needs to continue, not a conversation dump), **independent environment revalidation** (every checkpoint component is verified against the current environment before resume, with staleness propagating through the dependency graph), and **provenance-aware state** (every fact traces back to its origin, so agent-reported progress is never self-certifying).

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
> Two entrypoints are installed: `continuum` (the CLI) and `continuum-mcp`
> (the MCP server). The core library and CLI use only the standard library —
> the `mcp` extra is required solely for the server.

What runs today (Phases 1–7): record events, project state, checkpoint, survive a crash, validate against the current environment, never duplicate an external side effect, and decide how it is safe to resume.

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

### Run the proof yourself

Two scripts are the primary evidence, both verified end to end rather than
described:

```bash
python examples/crash_recovery_agent.py   # real process kill, real side effect
python scripts/mcp_smoke.py               # real subprocess, real JSON-RPC traffic
```

`crash_recovery_agent.py` starts a run, performs an external side effect, then
terminates the process with `os._exit(9)` — no cleanup, no flush — while the
dataset it depends on changes underneath it. It restarts, detects the change,
refuses to resume until the uncertain side effect is reconciled, and finishes
with the work not repeated and the side effect not duplicated.

`mcp_smoke.py` drives the MCP server as a subprocess over stdio and prints every
JSON-RPC frame as it crosses the wire. It asserts, rather than reports, that the
same action intercepted twice returns `proceed: false` with the prior result.

Both exit non-zero if their guarantees fail.

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

## MCP Integration

CONTINUUM ships an MCP server so an agent can record progress, checkpoint, and
route external side effects through the ledger without embedding the library.

```bash
uv pip install -e ".[mcp]"
CONTINUUM_MCP_MUTATING_CLIENTS=your-client-name continuum-mcp
```

Nine tools over stdio. Three are read-only (`validate`, `resume`,
`list_actions`); six mutate (`record_progress`, `checkpoint`,
`intercept_action`, `complete_action`, `fail_action`, `reconcile_action`).

**Side effects are two-phase.** A Python callable cannot cross the MCP
boundary, so the server cannot perform the effect itself:

1. `continuum_intercept_action` claims the ledger entry and answers *may I?*
2. the caller performs the effect
3. `continuum_complete_action` records the outcome

Between 1 and 3 the ledger holds a `STARTED` record. A caller that crashes or
never reports back leaves the action uncertain, and recovery refuses to resume
until it is reconciled. That is intended: an unreported effect is
indistinguishable from a completed one.

**Mutating tools deny by default.** Callers are matched against an allowlist
from `CONTINUUM_MCP_MUTATING_CLIENTS` (or `CONTINUUM_MCP_ALLOW`), or
`.continuum/mcp-policy.json`. An unconfigured server is read-only. Read-only
tools stay open to everyone, so asking "is this safe to resume?" never requires
permission.

**Agent-reported state is never self-certifying.** Everything written through
MCP is recorded with `Origin.EXTERNAL_AGENT` provenance, and the validator marks
it `REQUIRES_REVIEW`. An agent can report 9,999 of 10,000 documents complete and
CONTINUUM will still refuse to call the run safe to resume.

### Authentication is not implemented

`clientInfo` is asserted by the client during the initialize handshake and
never verified. A caller that wants to be seen as `claude-code` simply says so.

This is **authorization by declared identity, not authentication**. It keeps
honestly-named coexisting agents out of each other's runs — the situation this
project has actually been in, with several clients pointed at one database. It
does not defend against a deliberately impersonating local process, which in any
case can read and write the SQLite file directly.

Tracked as [#1](https://github.com/Cyrax321/CONTINUUM/issues/1).

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

### CLI

Standard library only — a recovery tool must not fail to import when you most need it.

```bash
continuum init                                   # create storage
continuum runs                                   # list runs
continuum inspect <run_id> [--version 17]        # semantic state, now or at a version
continuum history <run_id>                       # version and checkpoint history
continuum events <run_id> [--after N --upto M]   # raw event log
continuum diff <run_id> <from> <to>              # semantic diff between versions
continuum validate <run_id> --env dataset=v4     # validate. read-only
continuum resume <run_id> --env dataset=v4       # recovery decision + contract
continuum checkpoint <run_id>                    # force a checkpoint. mutates
continuum verify <run_id>                        # re-audit the event hash chain
continuum actions <run_id>                       # external side effects
continuum show-contract <run_id>                 # the machine-readable contract
continuum replay <run_id> [--upto N]             # re-derive state from events
```

Every command accepts `--json`. `inspect`, `history`, `events`, `diff`, `validate`, `resume`,
`verify`, `actions`, `show-contract` and `replay` never write, so they are safe against a live
database while an agent is mid-run.

#### Exit codes are a safety contract

```bash
continuum resume "$RUN" && ./start-agent.sh
```

That line must never launch an agent onto stale state, so **only a verified-safe run exits 0**:

| Code | Meaning |
|:--|:--|
| `0` | verified safe to resume |
| `10` | recoverable, but repairs are required first |
| `20` | a human must decide (typically an unreconciled side effect) |
| `30` | not safe to resume |
| `2` / `3` / `4` | not found / integrity failure / not implemented |

A recovery mode nobody has classified falls through to *unsafe*, never to `0`.

```text
$ continuum resume run_4821 --env dataset=v4

Recovery decision: REQUEST_HUMAN
  because 1 external side effect(s) have unknown outcomes

Repairs required:
  1. [auto]  reconcile_action action_cda6e307 — github.create_issue was interrupted
  2. [auto]  revalidate_dependency dataset — v3 -> v4
  3. [auto]  rederive_evidence paper_128 — source 'dataset' changed
  4. [auto]  rederive_finding finding_17 — rests on changed evidence: paper_128

Next permitted action: reconcile_action:action_cda6e307...
$ echo $?
20
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

### Action Ledger (Phase 6 — Complete)

Storage gives durability for *state*. It cannot give exactly-once semantics for effects on other systems, because the effect and the record of it are two separate writes with a gap between them. The ledger makes that gap observable instead of invisible.

```python
from continuum import ActionLedger, UnknownSideEffect

ledger = ActionLedger(store, "run_4821")

outcome = ledger.claim("github.create_issue", {"title": "Bug report"})
if outcome.fresh:
    issue = github.create_issue(...)
    ledger.complete(outcome.key, external_id=issue.id, result={"url": issue.url})
else:
    issue_id = outcome.external_id  # already done — previous result returned
```

**Every crash interleaving is accounted for:**

| Crash lands | Ledger state on recovery | Behaviour |
|:--|:--|:--|
| before the claim | nothing recorded | retry is safe |
| between claim and effect | `STARTED`, no result | **outcome unknown** |
| between effect and record | `STARTED`, no result | **outcome unknown** |
| after recording | `COMPLETED` | repeat returns stored result |

The middle two are indistinguishable from the ledger alone — which is exactly why they must not be resolved by assumption. `claim` raises `UnknownSideEffect` and requires a reconciler:

```python
from continuum import ProbeReconciler, Resolution, reconcile_pending

reconcile_pending(
    ledger,
    ProbeReconciler(
        lambda action: Resolution(occurred=True, external_id=find_issue(action)),
    ),
)
```

`ProbeReconciler` asks the external system and is the only strategy that produces evidence. `AssumeNotOccurredReconciler` retries, and requires you to assert `idempotent=True` explicitly so nobody reaches for it by reflex. `ManualReconciler` escalates.

There is deliberately **no `AssumeOccurred` strategy**. Assuming success without evidence silently drops work, and a dropped side effect is invisible — nothing in the system will ever contradict it. A probe that raises is treated as "could not determine", never as evidence of absence: an unreachable API tells you nothing about whether your earlier request landed.

This is honest **at-least-once with mandatory reconciliation**, not exactly-once. The gap is documented rather than marketed away.

Verified with real subprocesses — a worker that creates a GitHub issue then dies with `os._exit(9)` before recording it:

```text
=== RECOVERY ===
checkpoint v2: 60/100 docs, replayed 11 events
uncertain side effects: 1 -> ['github.create_issue']
refused blind retry (UNKNOWN_SIDE_EFFECT)
reconciled: confirmed as performed: github.create_issue

[!!] external dependency dataset: conflicted — v3 -> v4
[!!] evidence paper_128: stale — source 'dataset' changed
[!!] finding finding_17: stale — rests on changed evidence: paper_128
[ok] progress: valid — 60 completed

repeat claim -> fresh=False, external_id=481
completed 100/100 | events verified: True

=== external system ===
issue count: 1
```

Sixty documents not reprocessed, one dataset change detected and propagated, and **exactly one issue created** despite the crash.

### Recovery Engine (Phase 7 — Complete)

Validation says what is wrong. The ledger says what may have happened. The engine turns both into one decision.

```python
from continuum.recovery import RecoveryEngine

decision = RecoveryEngine(store).assess("run_4821", current_environment=now)

decision.mode  # RecoveryMode.REQUEST_HUMAN
decision.next_allowed_action  # "reconcile_action:action_011f511d"
decision.permits("rederive_finding:finding_17")  # False
```

**The most cautious applicable signal wins.** Each signal proposes a mode; the engine takes the maximum on an explicit ordering:

```text
RESUME < REPAIR_AND_RESUME < REPLAN < WAIT < REQUEST_HUMAN < ROLLBACK < ABORT
```

This matters because the signals co-occur. A run can have a stale dataset *and* an uncertain side effect at the same time. Returning whichever was noticed first would make recovery depend on iteration order — and the unsafe answer would win about half the time.

**Repairs are ordered by dependency, not discovery.** Reconciling an uncertain side effect always comes first: nothing else is safe while the world may or may not have been modified. A dependency is re-pinned before the evidence and findings derived from it, since repairing in the wrong order produces work that is stale the moment it finishes.

**The contract names exactly one next action.** Listing everything currently allowed would let an agent pick the convenient step and skip the reconciliation it was supposed to do first:

```text
run_id:            run_1
checkpoint:        v2
recovery_status:   requires_human
verified:          goal, progress
invalidated:       evidence:paper_128 (stale), external_dependency:dataset (conflicted),
                   finding:finding_17 (stale)
required_actions:
  - reconcile_action:action_011f511df03cf454
  - revalidate_dependency:dataset
  - rederive_evidence:paper_128
  - rederive_finding:finding_17
next_allowed:      reconcile_action:action_011f511df03cf454
```

Contracts are deterministic and sealed with an integrity hash — one that could be edited between issue and enforcement would gate nothing.

The engine is **read-only**. It computes and explains a decision without mutating the run, which is what makes assessment safe to perform against a live database.

Full run — crash, dataset change, and an interrupted side effect together:

```text
Recovery decision: REQUEST_HUMAN
  because 1 external side effect(s) have unknown outcomes

agent tries to skip ahead -> permitted? False
after reconciling         -> REPAIR_AND_RESUME, next: revalidate_dependency:dataset

=== external system === issues created: 1
```

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
|       +-- actions/
|       |   +-- __init__.py
|       |   +-- idempotency.py       Content-derived action identity
|       |   +-- ledger.py            Durable record of side effects
|       |   +-- reconciliation.py    Resolving uncertain outcomes
|       +-- recovery/
|       |   +-- __init__.py
|       |   +-- engine.py            Decide how a run may resume
|       |   +-- planner.py           Ordered repair steps
|       |   +-- contract.py          Sealed, gated next action
|       +-- cli/
|       |   +-- __init__.py
|       |   +-- main.py              argparse CLI, read-only by default
|       |   +-- exitcodes.py         Exit codes as a safety contract
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
    +-- test_action_ledger.py        Idempotency and the crash gap
    +-- test_reconciliation.py       Strategies + real-subprocess crash tests
    +-- test_recovery_engine.py      Decision precedence and contract gating
    +-- test_recovery_planner.py     Repair ordering and determinism
    +-- test_cli.py                  Exit-code contract and read-only guarantees
```

---

## CONTINUUM-Bench (design, not implemented)

**No benchmark harness exists.** Nothing in this section has been built or
measured, and `continuum benchmark` exits `4` saying so. The scenarios and
metrics below are a specification for future work, recorded so the intended
measurements are stated before any results are produced.

Design for evaluating long-running agent recovery under controlled failures.

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

---

## Roadmap

| Phase | Component                         | Status      |
|:-----:|:----------------------------------|:------------|
|   1   | Data models + Event system        | Complete    |
|   2   | Semantic state representation     | Complete    |
|   3   | SQLite persistence                | Complete    |
|   4   | Checkpoint creation               | Complete    |
|   5   | State validation                  | Complete    |
|   6   | Action ledger + Idempotency       | Complete    |
|   7   | Recovery engine                   | Complete    |
|   8   | CLI                               | Complete    |
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

## Known Limitations

- **MCP caller authentication** — `clientInfo` is asserted by the client during the handshake and never verified. The authorization layer distinguishes honestly-named callers; it does not defend against a deliberately impersonating local process. Tracked as [#1](https://github.com/Cyrax321/CONTINUUM/issues/1).
- **CI Node deprecation** — the workflows pin `actions/checkout@v4` and `actions/setup-python@v5` on Node 20, which GitHub is forcing onto Node 24. Works today; becomes a hard failure on GitHub's schedule. [#2](https://github.com/Cyrax321/CONTINUUM/issues/2).
- **Unbuilt components** — the benchmark suite (Phase 12), cloud API (Phase 13), and dashboard (Phase 14) do not exist. `continuum benchmark` exits `4` saying so. Framework adapters for OpenAI Agents SDK and LangGraph are planned, not built.

For a full account of what is verified, what is believed, and what is neither, see [STATUS.md](STATUS.md).

## Contributing

The project is in early development (Phases 1–8 and 10 complete). There are many components to build — storage engines, state validation, framework adapters, benchmark scenarios, documentation.

Open an issue before submitting large PRs.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
