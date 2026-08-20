# Adapter authoring guide

CONTINUUM talks to agent frameworks through *adapters*. An adapter is a thin
facade over storage, state, checkpointing, the action ledger and the recovery
engine. The recovery funnel is the set of adapters plus the discovery layer
that lets one recovery call work for any of them.

## The contract every adapter honors

All adapters subclass `continuum.adapters.AgentAdapter` (an ABC) and must
implement:

- `capture_state(run_id, state, *, environment=None, reason="")` -> checkpoint
- `restore_state(run_id, *, replay=True)` -> `SemanticState`
- `intercept_action(run_id, action_type, action_fn, arguments=None, *, volatile=(), scoped_to_run=True)` -> result
- `resume(run_id, *, current_environment=None, expected_model=None, replay=True)` -> `RecoveryDecision`

`resume` is the uniform recovery entry point. It returns a framework-agnostic
`RecoveryDecision`, so callers never need to know which framework produced the
run.

## Built-in adapters

| Name        | Class                     | Needs extra          |
|-------------|---------------------------|----------------------|
| `generic`   | `GenericAgentAdapter`     | nothing              |
| `langchain` | `LangChainAgentAdapter`   | `langchain`          |
| `langgraph` | `LangGraphAgentAdapter`   | `langgraph`          |
| `openai`    | `OpenAIAgentAdapter`      | `openai-agents`      |

Each takes `storage` as its first constructor argument and accepts a few
optional keyword arguments (for example `graph` for langgraph, or a
`state_to_semantic` extractor).

## Discovery and dispatch (the funnel)

Adapters are registered by name in a process-wide registry. Registration is
*lazy*: an adapter's heavy dependencies are only imported when the adapter is
actually requested, so importing `continuum` never drags in `langchain` or
`openai`.

```python
from continuum import list_adapters, get_adapter, recover

list_adapters()            # ["generic", "langchain", "langgraph", "openai"]
adapter_cls = get_adapter("generic")

# One call recovers any run through any registered adapter:
decision = recover("generic", run_id, storage, current_environment=env)
```

`get_adapter("unknown")` raises `ValueError` with the list of known names.
`recover("unknown", ...)` raises the same, before touching storage.

## Authoring a new adapter

1. Subclass `AgentAdapter` and implement the four abstract methods.
2. Keep the adapter's import of its framework dependency *lazy* (import it
   inside `__init__` or the methods that need it, not at module top), so the
   adapter is importable in environments without that dependency.
3. Provide a `resume` implementation. The simplest correct version delegates to
   `RecoveryEngine(storage).assess(run_id, ...)`; framework-specific adapters
   may first project framework state into a `SemanticState`.
4. Register it so the funnel can find it:

   ```python
   from continuum.adapters import register_adapter

   register_adapter("myfw", lambda: MyFrameworkAdapter)
   ```

5. Add a smoke test that constructs the adapter with an in-memory
   `SQLiteStorage`, seeds a run and checkpoint, and asserts `recover("myfw", ...)`
   returns a `RecoveryDecision`. Guard any framework-specific setup so the test
   skips cleanly when the dependency is absent.
