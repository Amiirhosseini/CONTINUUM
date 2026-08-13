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

