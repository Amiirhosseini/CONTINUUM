# BUILD: CONTINUUM

## Verifiable Semantic Recovery Layer for Long-Running AI Agents

You are a senior distributed-systems engineer, AI-agent infrastructure engineer, Python library maintainer, and research engineer.

Build a serious open-source project called:

# CONTINUUM

### Tagline

**Agents that can lose their context without losing their work.**

The project is a lightweight, framework-agnostic infrastructure layer for long-running AI agents.

---

# 1. THE PROBLEM

Modern AI agents perform long-running tasks involving:

* many LLM calls
* tool calls
* external APIs
* files
* databases
* browser sessions
* plans
* intermediate decisions
* evidence
* approvals
* human intervention
* changing environments

A long-running agent can fail because:

* the process crashes
* the machine restarts
* the deployment is replaced
* the model context is compacted
* the context window becomes too large
* a tool fails
* an API session expires
* the environment changes
* the agent changes models
* an external resource changes
* a previously valid decision becomes stale

A naïve agent often responds by replaying the entire task.

That causes:

* duplicated work
* duplicated API calls
* duplicated side effects
* higher cost
* lost decisions
* inconsistent state
* stale assumptions
* unreliable recovery

Existing durable execution and checkpointing systems address parts of this problem.

CONTINUUM should investigate a narrower problem:

> **Can an agent resume safely from a compact semantic representation of its task state, while independently verifying whether that state is still valid in the current environment?**

Do NOT build a generic agent framework.

Do NOT build another memory/RAG system.

Do NOT build another workflow orchestration framework.

Do NOT train a model.

The project must be CPU-first and lightweight.

---

# 2. CORE IDEA

CONTINUUM separates:

```text
LLM CONTEXT
from
DURABLE TASK STATE
```

The LLM context is temporary.

The semantic task state is durable.

Architecture:

```text
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
            └────────────> Resume
```

---

# 3. THE KEY DIFFERENTIATOR

Do NOT simply save:

```text
conversation history
```

Do NOT simply save:

```text
full agent state
```

Instead construct a compact:

# SEMANTIC CHECKPOINT

A checkpoint should represent the minimum verified information required to continue the task.

Example:

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
      "claim": "...",
      "evidence": ["paper_128"],
      "confidence": 0.91
    }
  ],

  "pending_work": [
    "Search 2019-2022 literature",
    "Resolve contradictory evidence"
  ],

  "external_dependencies": [
    {
      "resource": "dataset",
      "version": "v3"
    }
  ],

  "last_verified_environment": {
    "timestamp": "...",
    "hash": "..."
  }
}
```

The checkpoint must be:

* compact
* inspectable
* versioned
* deterministic where possible
* independently verifiable
* diffable
* recoverable
* serializable

---

# 4. MOST IMPORTANT CONCEPT:

# STATE VALIDATION

The system MUST NOT blindly trust an old checkpoint.

Before recovery:

```text
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

Example:

Checkpoint says:

```text
Dataset = v3
```

Current environment:

```text
Dataset = v4
```

CONTINUUM should produce:

```text
STATE VALIDATION FAILED

Dependency:
dataset

Checkpoint:
v3

Current:
v4

Affected state:
17 experiments

Recovery:
REQUIRES_REVALIDATION
```

The agent must NOT silently continue.

---

# 5. STATE STATUS

Every semantic state component should have a status:

```text
VALID
STALE
CONFLICTED
UNKNOWN
INVALID
REQUIRES_REVIEW
```

Example:

```text
Goal             VALID
Progress         VALID
Decision #12     STALE
Evidence #81     VALID
Dataset          CONFLICTED
Approval         EXPIRED
```

This should be exposed through the API.

---

# 6. ACTION LEDGER

Create an idempotent action ledger.

The system must remember external side effects.

Example:

```json
{
  "action_id": "action_812",
  "type": "github.create_issue",
  "arguments_hash": "...",
  "status": "COMPLETED",
  "external_id": "481",
  "timestamp": "...",
  "result_hash": "..."
}
```

If the agent crashes after creating issue #481:

On recovery:

```text
Agent:
Create GitHub issue.

CONTINUUM:
Action already completed.

External ID:
#481

Returning previous result.
```

This prevents duplicate side effects.

Support action states:

```text
PLANNED
STARTED
COMPLETED
FAILED
UNKNOWN
COMPENSATED
REQUIRES_REVIEW
```

Important:

If the system cannot determine whether an external side effect occurred, it must NOT blindly retry.

It should return:

```text
UNKNOWN_SIDE_EFFECT
```

and require a reconciliation strategy.

---

# 7. CHECKPOINT STRATEGY

Do NOT checkpoint every turn by default.

Implement configurable checkpoint policies.

Examples:

```yaml
checkpoint:
  mode: semantic

  triggers:
    - important_state_change
    - external_side_effect
    - milestone
    - context_pressure
    - explicit_request

  max_interval_seconds: 300
```

The system should support:

```text
manual
interval
event-driven
semantic
hybrid
```

---

# 8. SEMANTIC STATE EXTRACTION

Implement a pluggable state extractor.

Architecture:

```python
class StateExtractor:
    def extract(self, trajectory, environment): ...
```

Provide:

### Deterministic extractor

Uses:

* explicit task metadata
* tool calls
* action results
* state transitions
* structured outputs

### Optional LLM extractor

Uses an external LLM only when enabled.

The system MUST work without an LLM.

Do not require OpenAI, Anthropic, Gemini, or any proprietary provider.

---

# 9. CONTEXT RECONSTRUCTION

When the agent resumes, CONTINUUM constructs a bounded recovery context:

```text
CURRENT GOAL

VERIFIED PROGRESS

VALID DECISIONS

UNRESOLVED QUESTIONS

RECENT ACTIONS

RELEVANT EVIDENCE

PENDING TASKS

STALE STATE

ENVIRONMENT CHANGES

NEXT SAFE ACTION
```

Do NOT simply dump the complete previous transcript.

The goal is:

> **minimum sufficient recovery context.**

---

# 10. RECOVERY MODES

Support:

```text
RESUME
REPAIR_AND_RESUME
ROLLBACK
WAIT
REQUEST_HUMAN
ABORT
```

Example:

```text
Checkpoint valid
→ RESUME

Checkpoint partially stale
→ REPAIR_AND_RESUME

External side effect uncertain
→ REQUEST_HUMAN

Critical dependency changed
→ ABORT or REPLAN
```

---

# 11. RECOVERY CONTRACT

Before allowing the agent to resume, CONTINUUM should generate a recovery contract.

Example:

```json
{
  "run_id": "run_4821",

  "recovery_status": "SAFE_TO_RESUME",

  "verified": [
    "goal",
    "completed_documents",
    "evidence"
  ],

  "invalidated": [
    "dataset_v3"
  ],

  "required_actions": [
    "revalidate experiment results"
  ],

  "next_allowed_action": "revalidate_dataset"
}
```

This contract should be deterministic and machine-readable.

---

# 12. ENVIRONMENT SNAPSHOT

Create an environment abstraction.

The environment may contain:

```text
files
database records
API resources
dataset versions
Git commits
configuration
permissions
tool availability
external IDs
```

Create:

```python
EnvironmentSnapshot
```

with:

```python
capture()
compare()
diff()
validate()
```

Example:

```text
ENVIRONMENT DIFF

dataset:
v3 → v4

git:
abc123 → def456

permissions:
write_access → revoked

API:
session_valid → expired
```

---

# 13. STATE DIFF

Provide:

```bash
continuum diff checkpoint_a checkpoint_b
```

Output:

```text
+ New finding: finding_81
~ Dataset version: v3 → v4
- Decision #7 invalidated
+ Pending task: re-run experiment
```

Also provide:

```python
state.diff(other_state)
```

---

# 14. STATE VERSIONING

Every state mutation must produce a version.

Example:

```text
v0
 ↓
v1
 ↓
v2
 ↓
v3
```

Use immutable event records where practical.

Support:

```bash
continuum history run_4821
```

and:

```bash
continuum inspect run_4821 --version 17
```

---

# 15. EVENT LOG

Create an append-only event model.

Events include:

```text
RUN_STARTED
TASK_UPDATED
TOOL_CALLED
TOOL_COMPLETED
TOOL_FAILED
DECISION_CREATED
DECISION_INVALIDATED
EVIDENCE_ADDED
STATE_CHECKPOINTED
STATE_VALIDATED
ENVIRONMENT_CHANGED
RECOVERY_STARTED
RECOVERY_COMPLETED
RECOVERY_BLOCKED
ACTION_RECONCILED
```

The event log should be the source of truth where practical.

---

# 16. CRASH RECOVERY DEMO

Create a complete example.

Example:

```text
examples/
    crash_recovery_agent.py
```

The example should:

1. Start a long-running task.
2. Process several items.
3. Save semantic state.
4. Simulate process termination.
5. Modify the environment.
6. Restart the process.
7. Load the checkpoint.
8. Validate the state.
9. Detect the environmental change.
10. Repair the affected state.
11. Resume execution.
12. Finish without repeating completed work.

The README MUST show this demo.

---

# 17. CONTEXT COMPACTION DEMO

Create:

```text
examples/context_compaction.py
```

Simulate:

```text
large context
→ compaction
→ loss of transcript
→ semantic checkpoint survives
→ recovery context reconstructed
→ task continues
```

Measure:

```text
original context tokens
recovery context tokens
task completion
recovery correctness
```

---

# 18. MODEL-SWITCH DEMO

Create:

```text
examples/model_switch.py
```

Simulate:

```text
Model A
 ↓
checkpoint
 ↓
Model unavailable
 ↓
Model B
 ↓
recover
```

The agent should retain:

* task goal
* verified progress
* decisions
* evidence
* pending work

without requiring the original model's full conversation.

The system must NOT assume that switching models is automatically safe.

If a model-specific assumption exists, mark it:

```text
MODEL_SPECIFIC_STATE
```

and require validation.

---

# 19. FRAMEWORK ADAPTERS

Build the core framework-agnostic.

Create adapters for:

```text
generic Python agent
OpenAI Agents SDK
LangGraph
```

Only implement adapters when they can be done cleanly.

Do not tightly couple the core to these frameworks.

Adapter interface:

```python
class AgentAdapter:
    def capture_state(...)
    def restore_state(...)
    def intercept_action(...)
    def resume(...)
```

---

# 20. CLI

Implement:

```bash
continuum init
continuum run
continuum checkpoint
continuum resume
continuum inspect
continuum diff
continuum validate
continuum history
continuum replay
continuum benchmark
```

Example:

```bash
continuum resume run_4821
```

Output:

```text
CONTINUUM RECOVERY

Run: run_4821

Checkpoint:
v17

State validation:
✓ Goal
✓ Progress
✓ Evidence
⚠ Dataset version changed
✓ Action ledger

Recovery decision:
REPAIR_AND_RESUME

Repair:
Revalidate experiments 14–17

Next permitted action:
dataset_revalidation
```

---

# 21. PYTHON API

Keep the API extremely simple.

Example:

```python
from continuum import Continuum

runtime = Continuum(storage="sqlite:///agent.db")

run = runtime.start(goal="Analyze these documents")

run.checkpoint()

run.record_action(...)

run.complete()
```

Recovery:

```python
run = runtime.resume("run_4821")

status = run.validate()

if status.safe:
    run.continue_execution()
```

---

# 22. STORAGE

MVP:

```text
SQLite
```

Optional:

```text
PostgreSQL
```

Optional object storage:

```text
S3-compatible
```

Do NOT require a cloud database.

A developer must be able to run the entire system locally.

---

# 23. CLOUD ARCHITECTURE

Create optional cloud deployment:

```text
                  AGENT
                    │
                    ▼
              CONTINUUM SDK
                    │
                    ▼
               API Gateway
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
     State Service       Event Service
          │                   │
          └─────────┬─────────┘
                    ▼
               PostgreSQL
                    │
                    ▼
              Object Storage
```

Use:

* FastAPI
* PostgreSQL
* Docker
* optional Redis
* optional S3-compatible object storage

No GPU.

The cloud service should primarily provide:

* durable storage
* centralized run management
* multi-agent coordination
* recovery history
* state inspection

---

# 24. SECURITY

This is critical.

Never treat the checkpoint as trusted merely because it is persisted.

Validate:

* integrity
* version
* authorization
* provenance
* environment compatibility

Support cryptographic hashes for:

* checkpoints
* evidence
* action records
* environment snapshots

Do not store secrets inside semantic checkpoints.

Credentials must be referenced, never serialized into state.

---

# 25. RESEARCH BENCHMARK

Create:

# CONTINUUM-Bench

Evaluate long-running agents under controlled failures.

Scenarios:

```text
process crash
context compaction
tool failure
API timeout
dataset change
file modification
permission change
model switch
external side effect
stale decision
partial completion
```

Each scenario should have ground-truth recovery behavior.

Example:

```json
{
  "scenario": "dataset_change",
  "checkpoint_version": "v3",
  "environment_version": "v4",
  "expected": "REPAIR_AND_RESUME"
}
```

Measure:

### Recovery correctness

Did the agent resume correctly?

### Duplicate work

How much previously completed work was repeated?

### Duplicate side effects

How many external actions were accidentally repeated?

### Recovery latency

How long until safe continuation?

### Recovery context size

How many tokens were required?

### State validation accuracy

Were stale states detected?

### Cost

How much LLM/API cost was saved?

---

# 26. BASELINES

Compare CONTINUUM against:

```text
1. Full transcript replay
2. Simple conversation summarization
3. Naive checkpointing
4. Structured task summary
5. CONTINUUM semantic checkpoint
```

Do NOT fabricate results.

Implement the benchmark harness first.

Run experiments only after the system is complete.

---

# 27. KEY RESEARCH METRIC

Introduce:

# Recovery Fidelity

Define a measurable metric for whether the recovered agent behaves consistently with a fault-free execution.

For example:

```text
Recovery Fidelity =
correct recovered decisions
/
required recovered decisions
```

Also measure:

```text
State Fidelity
Action Fidelity
Goal Fidelity
Evidence Fidelity
```

Clearly document the definitions.

---

# 28. SECOND RESEARCH METRIC

Introduce:

# Recovery Compression Ratio

Measure:

```text
Full historical context size
/
Semantic recovery state size
```

Example:

```text
Full transcript:
182,000 tokens

Recovery state:
4,200 tokens

Compression ratio:
43.3×
```

Do NOT claim this number until experimentally measured.

---

# 29. IMPORTANT RESEARCH QUESTION

The project should investigate:

> **How much agent execution history can be removed while preserving safe task continuation?**

Secondary questions:

1. Does semantic state outperform naïve summarization?
2. Can stale state be detected automatically?
3. How much duplicate work can durable semantic state eliminate?
4. How does recovery behave across different models?
5. How does recovery behave after environment changes?
6. Can external side effects be safely reconciled?

---

# 30. README POSITIONING

The README should NOT claim:

> "The first durable agent framework."

That is not defensible.

Instead:

> **CONTINUUM is a lightweight semantic recovery layer for long-running AI agents. It externalizes the minimum verified task state needed to survive crashes, context loss, and environmental changes.**

Then immediately show:

```text
Agent crashes.
Context disappears.
CONTINUUM remembers what actually matters.
```

---

# 31. README DEMO

The first screen of the README should show:

```bash
pip install continuum-agent
```

Then:

```python
from continuum import Continuum

runtime = Continuum("agent.db")

run = runtime.start(goal="Analyze 10,000 documents")

...
```

Then a crash:

```text
💥 PROCESS TERMINATED
```

Then:

```bash
continuum resume run_4821
```

Output:

```text
✓ 3,421 documents already processed
✓ 127 findings preserved
✓ 14 decisions preserved
⚠ dataset changed
✓ affected state identified
→ revalidation required
→ safe recovery
```

This should be the project's 30-second pitch.

---

# 32. REPOSITORY STRUCTURE

Use:

```text
continuum/
│
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── CHANGELOG.md
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
│
├── src/
│   └── continuum/
│       ├── __init__.py
│       ├── runtime.py
│       ├── models.py
│       ├── events.py
│       ├── state/
│       │   ├── semantic.py
│       │   ├── extractor.py
│       │   ├── validator.py
│       │   ├── versioning.py
│       │   └── diff.py
│       │
│       ├── recovery/
│       │   ├── engine.py
│       │   ├── planner.py
│       │   └── contract.py
│       │
│       ├── actions/
│       │   ├── ledger.py
│       │   ├── idempotency.py
│       │   └── reconciliation.py
│       │
│       ├── environment/
│       │   ├── snapshot.py
│       │   ├── validator.py
│       │   └── diff.py
│       │
│       ├── storage/
│       │   ├── base.py
│       │   ├── sqlite.py
│       │   └── postgres.py
│       │
│       ├── adapters/
│       │   ├── base.py
│       │   ├── generic.py
│       │   ├── openai.py
│       │   └── langgraph.py
│       │
│       ├── cli/
│       │   └── main.py
│       │
│       └── security/
│           ├── hashing.py
│           └── validation.py
│
├── tests/
│
├── examples/
│
├── benchmarks/
│
├── docs/
│
└── cloud/
    ├── api/
    └── deployment/
```

---

# 33. TESTING

Use:

* pytest
* hypothesis/property-based testing where useful
* mypy or pyright
* Ruff
* integration tests
* crash simulation tests

Test especially:

```text
crash during action
crash after action but before ledger commit
crash after ledger commit
duplicate recovery
stale checkpoint
environment change
model switch
partial state
corrupted checkpoint
unknown external side effect
concurrent state update
```

The action ledger must be tested heavily.

---

# 34. DISTRIBUTED-SYSTEM CORRECTNESS

Treat recovery as a distributed systems problem.

Explicitly reason about:

```text
exactly-once vs at-least-once
idempotency
atomicity
race conditions
partial failure
event ordering
eventual consistency
stale reads
concurrent updates
```

Do not claim exactly-once semantics unless actually implemented.

When guarantees are weaker, document them honestly.

---

# 35. PERFORMANCE TARGETS

MVP should run:

* CPU only
* locally
* without downloading models
* with SQLite
* with minimal memory
* with minimal latency

Semantic extraction through an LLM must be optional.

The deterministic core should remain fully functional offline.

---

# 36. DEVELOPMENT PHASES

Implement incrementally.

## Phase 1

Data models + event system.

## Phase 2

Semantic state representation.

## Phase 3

SQLite persistence.

## Phase 4

Checkpoint creation.

## Phase 5

State validation.

## Phase 6

Action ledger + idempotency.

## Phase 7

Recovery engine.

## Phase 8

CLI.

## Phase 9

Crash recovery examples.

## Phase 10

Environment snapshots and diffs.

## Phase 11

Framework adapters.

## Phase 12

Benchmark suite.

## Phase 13

Cloud API.

## Phase 14

Dashboard.

DO NOT build the dashboard first.

---

# 37. GITHUB QUALITY

The project must feel like a real open-source infrastructure project.

Include:

* clean README
* architecture diagram
* quickstart
* API docs
* examples
* benchmark
* tests
* contribution guide
* issue templates
* PR template
* GitHub Actions
* releases
* changelog

Add labels:

```text
good first issue
help wanted
detector
adapter
benchmark
documentation
research
```

Make extension points obvious.

---

# 38. EXTENSIBILITY

Developers should eventually be able to implement:

```python
class StatePlugin: ...
```

and:

```python
class EnvironmentProvider: ...
```

and:

```python
class ActionReconciler: ...
```

and:

```python
class RecoveryStrategy: ...
```

The core should remain small.

---

# 39. PRODUCT PHILOSOPHY

CONTINUUM is NOT:

* an LLM
* a chatbot
* an agent framework
* a vector database
* a RAG framework
* a workflow engine
* a generic memory system

CONTINUUM IS:

> **A reliability layer that makes long-running agent work durable, inspectable, and recoverable.**

The core abstraction is:

```text
semantic state
+
environment validation
+
action reconciliation
=
safe recovery
```

---

# 40. CRITICAL RULE

Before implementing a feature, check whether the feature already exists in established agent runtimes.

Do not duplicate functionality merely to increase feature count.

When existing functionality is similar, explicitly document:

```text
Existing approach:
...

CONTINUUM difference:
...
```

The project's differentiation should be based on measurable behavior and architecture, not marketing language.

---

# 41. FINAL ACCEPTANCE TEST

The finished MVP must successfully demonstrate this scenario:

```text
1. Agent starts long-running task.

2. Agent processes 100 items.

3. CONTINUUM creates semantic checkpoint.

4. Agent performs external side effect.

5. CONTINUUM records the action.

6. Process crashes.

7. Environment changes.

8. Process restarts.

9. CONTINUUM loads checkpoint.

10. CONTINUUM detects environment change.

11. CONTINUUM marks affected state stale.

12. CONTINUUM prevents unsafe replay.

13. Agent reconciles the stale state.

14. Agent resumes from verified progress.

15. Previously completed work is not repeated.

16. Previously completed external side effects are not duplicated.

17. Task completes.

18. CONTINUUM produces a complete recovery report.
```

The demo should be reproducible with one command.

---

# 42. FINAL INSTRUCTION TO YOU

Do not generate the entire codebase in one response.

Work incrementally.

Start with:

**Phase 1 — Data models + event system + tests.**

After implementing Phase 1:

1. run the tests
2. inspect failures
3. fix them
4. show the resulting file tree
5. explain the design briefly
6. wait for confirmation before moving to Phase 2

Do not skip tests.

Do not invent APIs.

Do not fabricate benchmark results.

Do not claim novelty that has not been established.

Prioritize correctness, minimalism, reproducibility, and real developer usefulness over flashy features.

The final goal is a project that can become a serious open-source repository and a credible AI-systems research artifact.
