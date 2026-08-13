# CONTINUUM architecture diagram

A complete view of the system: agents and clients, the framework adapters, the
deny-by-default MCP server, the SDK internals (state engine, event log, action
ledger, checkpointing, validation, recovery engine, security), the semantic
state data model, durable storage, and the external systems a run acts on.

## System architecture

```mermaid
flowchart TB
    %% Clients and agents
    subgraph C["Agents and clients"]
        direction LR
        cc["Claude Code"]
        lg["LangGraph agent"]
        oa["OpenAI agent"]
        gn["Generic Python agent"]
    end

    %% Adapters
    subgraph A["Framework adapters (optional installs)"]
        direction LR
        alg["LangGraphAdapter"]
        aoa["OpenAIAgentAdapter"]
        agn["GenericAgentAdapter"]
    end

    %% MCP server
    subgraph M["MCP server (stdio, deny by default)"]
        tools["9 tools<br/>read-only: validate, resume, list_actions<br/>mutating: record_progress, checkpoint,<br/>intercept_action, complete_action,<br/>fail_action, reconcile_action"]
        auth["Auth gate<br/>allowlist: CONTINUUM_MCP_MUTATING_CLIENTS<br/>or .continuum/mcp-policy.json"]
    end

    %% SDK
    subgraph S["CONTINUUM SDK (standard library only)"]
        direction TB
        subgraph SE["State engine"]
            ext["Extractors<br/>DeterministicExtractor (default, folds log)<br/>LLMExtractor (adds only, Origin.LLM, REQUIRES_REVIEW)"]
            proj["Semantic projection<br/>state = reduce(apply, events)<br/>reproducible + prefix-closed"]
            vers["Versioning<br/>content-addressed, linked,<br/>commit returns None if unchanged"]
            diff["Semantic diff"]
        end
        elog["Event log<br/>append-only, hash-chained<br/>29 event types<br/>verify() re-walks chain, localizes tamper"]
        led["Action ledger<br/>claim then perform then complete<br/>idempotent by resource key<br/>reconcilers: Probe (evidence), Manual, AssumeNotOccurred"]
        ckpt["Checkpoint manager<br/>6 policies: Manual, Interval, Event,<br/>Semantic, ContextPressure, Hybrid<br/>plus bounded recovery context"]
        env["Environment<br/>snapshot + conservative diff"]
        val["Validator<br/>staleness propagation<br/>dependency goes to evidence goes to finding goes to decision"]
        rec["Recovery engine<br/>planner + sealed contract<br/>7 modes, most cautious wins"]
        sec["Security<br/>canonical hashing, provenance,<br/>credentials never stored"]
        sm["SemanticState<br/>Goal, Progress, PlanStep, Decision,<br/>Finding, Evidence, PendingWork,<br/>Approval, ExternalDependency, ModelState"]
    end

    %% Storage
    subgraph D["Durable storage"]
        sql["SQLiteStorage<br/>WAL, synchronous FULL<br/>atomic sequence, integrity on read<br/>ConcurrentWriteError on race"]
    end

    %% External
    subgraph X["External systems"]
        gh["GitHub, email, APIs"]
    end

    %% Flows
    C --> A
    C --> M
    A --> S
    M --> auth
    auth --> tools
    tools --> S
    tools -->|intercept, then caller performs| X
    S --> elog
    elog --> sql
    elog --> proj
    proj --> vers
    proj --> val
    proj --> sm
    env --> val
    val --> rec
    led --> rec
    rec --> sql
    ckpt --> sql
    led -->|claim and complete| X
    X -->|outcome| led
    sec -. secures .-> elog
    sec -. secures .-> vers
    sec -. tags .-> sm
```

## Enumerated reference (complete data)

| Item | Values |
|:--|:--|
| **MCP tools (9)** | Read-only (3): `validate`, `resume`, `list_actions`. Mutating (6): `record_progress`, `checkpoint`, `intercept_action`, `complete_action`, `fail_action`, `reconcile_action`. |
| **Recovery modes (7)** | `RESUME`, `REPAIR_AND_RESUME`, `REPLAN`, `WAIT`, `REQUEST_HUMAN`, `ROLLBACK`, `ABORT`. Precedence (most cautious wins): `RESUME -> REPAIR_AND_RESUME -> REPLAN -> WAIT -> REQUEST_HUMAN -> ROLLBACK -> ABORT`. |
| **Checkpoint policies (6)** | `ManualPolicy`, `IntervalPolicy`, `EventPolicy`, `SemanticPolicy`, `ContextPressurePolicy`, `HybridPolicy` (default). |
| **Action ledger reconcilers (3)** | `ProbeReconciler` (asks external system, produces evidence), `ManualReconciler` (escalates), `AssumeNotOccurredReconciler` (requires explicit `idempotent=True`). Deliberately no `AssumeOccurred`. |
| **SemanticState fields (10)** | `Goal`, `Progress`, `PlanStep[]`, `Decision[]`, `Finding[]`, `Evidence[]`, `PendingWork[]`, `Approval[]`, `ExternalDependency[]`, `ModelState`. |
| **Event types (29)** | Including `RUN_STARTED`, `TOOL_CALLED`, `DECISION_CREATED`, `STATE_CHECKPOINTED`, `ENVIRONMENT_CHANGED`, `RECOVERY_STARTED`, `ACTION_RECONCILED`, `WORK_COMPLETED`, `RUN_COMPLETED`, and 20 more across the full lifecycle. |
| **Action states** | `PLANNED`, `STARTED`, `COMPLETED`, `FAILED`, `UNKNOWN`, `COMPENSATED`, `REQUIRES_REVIEW`. |
| **Storage guarantees** | Append-only events, atomic sequence allocation, durability on `append_event` return, WAL journaling, `synchronous=FULL`, corruption refused on read (`CorruptedRecord`), loud write races (`ConcurrentWriteError`). No exactly-once (the ledger reconciles the gap). |
| **Framework adapters (3)** | `GenericAgentAdapter` (in-process, trusted `Origin.DETERMINISTIC`), `OpenAIAgentAdapter` (OpenAI Agents SDK), `LangGraphAdapter` (wraps a `StateGraph`). |
| **Provenance / origin** | Every state component traces to its origin event: `Origin.DETERMINISTIC`, `Origin.EXTERNAL_AGENT` (marked `REQUIRES_REVIEW`), `Origin.LLM`. |

## Recovery data flow

```mermaid
sequenceDiagram
    participant Agent
    participant MCP as MCP server
    participant Ledger as Action ledger
    participant Store as SQLite
    participant Validator
    participant Engine as Recovery engine
    participant Ext as External system

    Agent->>MCP: intercept_action(key)
    MCP->>Ledger: claim(action, key)
    Ledger->>Store: write STARTED
    Agent->>Ext: perform side effect
    Agent->>MCP: complete_action(key, external_id)
    MCP->>Ledger: complete -> COMPLETED
    Note over Agent,Ext: crash between claim and complete
    Ledger->>Engine: outcome UNKNOWN
    Engine->>Validator: validate environment
    Validator-->>Engine: staleness report
    Engine->>Agent: contract (REQUEST_HUMAN)
    Agent->>Ledger: reconcile_action (ProbeReconciler)
    Ledger->>Ext: probe outcome
    Ext-->>Ledger: occurred=True, external_id
    Ledger->>Store: COMPLETED (no duplicate effect)
```
