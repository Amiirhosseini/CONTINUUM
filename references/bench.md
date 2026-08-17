## CONTINUUM-Bench

A recovery benchmark for long-running agents under controlled failures. The
minimal harness now ships: `continuum benchmark` runs real scenarios against the
actual library (storage, checkpointing, validation, action ledger, recovery)
with an in-process simulated agent. Nothing is mocked and no result is invented.

### Status

Implemented (minimal harness):

- Module: `src/continuum/benchmark/__init__.py`
- Command: `continuum benchmark [--total N] [--json]` (default total 200)
- Tests: `tests/test_benchmark.py` asserts that continuum resumes with 0
  duplicate work, detects the dataset change, and that full replay wastes work

Remaining Phase 12 goals (see STATUS.md):

- Expand from the 3 shipped scenarios to the full scenario suite below.
- Publish baselines from real agent runs, not just the simulated harness.
- Add a dashboard view of results.

### Implemented scenarios

| Scenario             | What breaks                                       |
|:---------------------|:--------------------------------------------------|
| process_crash        | The agent dies mid-run; measures duplicate work   |
| dataset_change       | The environment version changes while the agent is down |
| unknown_side_effect  | An external side effect is interrupted mid-flight |

### Implemented methods (baselines)

- `continuum`        - semantic checkpoint + environment revalidation + ledger
- `replay`           - full transcript replay from scratch (the waste case)
- `naive_checkpoint` - resume from the saved progress count, no validation

### Metrics

| Metric                       | Definition                                     |
|:-----------------------------|:-----------------------------------------------|
| duplicate_work_ratio         | Previously completed work repeated after recovery |
| duplicate_side_effects       | External actions accidentally repeated          |
| detected_stale               | Whether the method noticed the environment changed |
| context_tokens               | Size of the briefing the agent needs to resume |
| compression_ratio            | full log tokens / resume briefing tokens       |
| elapsed_seconds              | Time to run the (scenario, method) measurement |

### Target scenario suite (not yet implemented)

The full spec calls for ten controlled-failure scenarios:

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

### Sample results

From `continuum benchmark --total 30` (illustrative, not the published baseline):

    scenario           method              dup_work  dup_side  stale  ctx_tok  compress
    process_crash      continuum              0.000         0  False       57     14.16
    process_crash      replay                 0.500         1  False      778       1.0
    process_crash      naive_checkpoint       0.000         0  False        4      None
    dataset_change     continuum              0.000         0   True       57     14.16
    dataset_change     replay                 0.500         1  False      778       1.0
    dataset_change     naive_checkpoint       0.000         0  False        4      None
    unknown_side_effect continuum              0.000         0  False       57     13.86
    unknown_side_effect replay                 0.233         1  False      516       1.0
    unknown_side_effect naive_checkpoint       0.000         0  False        3      None

Reading: continuum resumes with no duplicate work and exactly one side effect,
and is the only method that detects the dataset change. Full replay reprocesses
everything (wasteful but ends correct). Naive checkpoint is efficient but blind.
