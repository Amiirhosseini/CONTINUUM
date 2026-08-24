# CONTINUUM MCP test report

Adversarial verification of the CONTINUUM MCP server: all 11 registered tools,
their failure modes, and the guarantees that must not move.

- **Date:** 2026-08-24
- **Commit under test:** `bafc15a` on `fix/mcp-idempotency-and-diagnostics`
- **Baseline:** `b3472df` on `main`
- **Environment:** darwin 25.2.0, Python 3.14.5, continuum-agent 0.1.0 editable
- **Related:** PR #311, issues #306 to #309

## Result

| Suite | Result |
|---|---|
| `python -m pytest` | 1359 passed, 24 skipped, stable across 3 consecutive runs |
| `ruff check` / `ruff format --check` | clean on every changed file |
| `mypy src` | 25 errors, identical to baseline (missing stubs for the optional `mcp` extra and `cryptography`) |
| In-process audit, all 11 tools | 23 of 23 assertions passed |
| Adversarial probe round 2 | 14 of 14 assertions passed |
| Live MCP audit through the running server | all fixes confirmed present |

Seven defects were found across two rounds. Three are fixed in the first commit,
three in the second, and one was withdrawn as not-a-bug.

## Method

Three complementary levels, because each catches what the others miss.

1. **Live MCP tools.** Driven through the actual running `continuum-mcp` process
   over stdio, as a real client would. This is the only level that proves the
   deployed server behaves correctly, and it caught that a restart is required
   before code changes take effect.
2. **In-process dispatch.** `server.call_tool(...)` against a `:memory:` store,
   which exercises argument coercion and JSON serialisation without needing a
   restart. Used for the exhaustive matrix and for the regression assertions.
3. **Unit and integration suite.** `pytest`, to confirm no existing guarantee
   regressed.

Every finding below was reproduced at level 1 or 2 before being fixed, and each
fix carries a test that fails without it.

## Tool coverage

All 11 tools were exercised. None was covered by inspection alone.

| Tool | Exercised with |
|---|---|
| `continuum_record_progress` | valid, `completed > total`, negative counters, blank and whitespace `run_id`, unicode goal |
| `continuum_record_summary` | full structured payload, 20 KB oversized note |
| `continuum_checkpoint` | with and without `env`, unknown run, version increment |
| `continuum_validate` | no `env`, matching `env`, drifted `env`, `expected_model`, unknown run |
| `continuum_resume` | by id, no id (active-run path), unknown run, `expected_model`, both guidance branches |
| `continuum_confirm` | refusal without an operator token |
| `continuum_intercept_action` | fresh, dedup by key, varied arguments, blank `action_type`, at budget, beyond budget |
| `continuum_complete_action` | valid, bogus key, with and without `external_id` |
| `continuum_fail_action` | `certain=true`, `certain=false` |
| `continuum_reconcile_action` | `occurred` true and false, on unknown, started, failed and completed actions, bogus key |
| `continuum_list_actions` | resolved and unresolved rows, unknown run |

## Findings

### 1. Retry budget defeated idempotency (issue #309, high)

The budget gate ran before the deduplication lookup, and dedup lives inside
`ledger.claim()`. Once an action type reached its budget, re-claiming an action
that had already **completed** raised `ToolError` instead of returning
`proceed=false` with the stored result.

This inverts the tool's central promise. An agent that receives an error where it
expected "already done, reuse this" cannot distinguish "I must not repeat this"
from "the ledger is unavailable", and the plausible recovery is to perform the
side effect again outside the ledger. The mechanism that exists to stop a card
being charged twice could, at budget, be the reason it was.

The same function also counted successes as retries, tallying every claim slot per
type regardless of outcome, so three successful distinct operations exhausted a
budget of 3 and the fourth was refused having never retried anything.

Found by being blocked by it: after filing three issues through the ledger, the
fourth was refused. Issue #309 had to be filed outside the ledger.

**Fixed.** The gate now runs only when a claim would genuinely open a new slot;
`COMPLETED` and `UNKNOWN` records still answer. Claim slots whose action reached
`COMPLETED` no longer count. Failures, unknowns and in-flight attempts still
count, so the amplification guard from #240 is intact, and counting stays
per-type because that is what catches an agent re-planning with varied arguments.

### 2. Inverted diagnostic when `env` is omitted (issue #307, medium)

After a checkpoint pinned dependencies, `validate` and `resume` without `env`
reported `"no environment snapshot to compare against"`. The snapshot was not
missing; the checkpoint recorded it, and passing `env` proves it. What was absent
was the caller's current observation, so the message named the one thing
definitely present.

**Fixed.** The detail now reads
`no current version supplied for comparison; pass env={"dataset": "<version>"}`.

The `UNKNOWN` status is unchanged, deliberately. An earlier plan to make an
unobserved dependency non-blocking would have broken
`test_no_environment_at_all_leaves_dependencies_unverified` and its stated
principle, "never validated is not the same as validated clean". That test is
correct. Only the wording was wrong, so only the wording changed.

### 3. `expected_model` silently inert (issue #308, medium)

Drift detection needs both sides of the comparison, and `recorded` comes from
`state.model`, populated only by `MODEL_CHANGED` / `MODEL_ASSUMPTION_RECORDED`.
Nothing on the MCP path emits either, so with no assumptions recorded the check
returned silently and the result was byte for byte identical to a clean
comparison. A caller passing `expected_model` reasonably concluded it had ruled
out drift. It had ruled out nothing.

**Fixed.** The gap is reported as an explicit `model` component with status
`unknown`. This is the same fail-open pattern #49 closed for model-specific
assumptions, one branch over, and honours the comment already in that function:
"Say so rather than guessing valid in the state's favour."

Routes to `REQUIRES_REPAIR` rather than `REQUIRES_HUMAN`, which is the right
severity: the remedy is to record which model produced the state, and that is
mechanical rather than a judgement call.

### 4. Blank `run_id` accepted (high)

`continuum_record_progress(run_id="")` created a run. Not cosmetic: a blank id
wins `get_active_run`, so it silently became the run a fresh session was told to
resume, displacing real work. It also rendered unusable guidance, literally
`continuum confirm ` with nothing after it, and is indistinguishable from "no
run" at every boundary that takes a run id.

**Fixed.** `Storage.require_usable_run_id` refuses blank and whitespace-only ids,
called from all four create paths across both backends.

Enforced on the **write** path, not on the `Run` model. A model-level constraint
also runs on deserialization, so a single pre-existing bad row made `list_runs`
and `get_active_run` raise, leaving an operator unable to even see the row in
order to clean it up. This was not theoretical: the first attempt at this fix
broke `continuum runs` against the live database. Guarding the entry point stops
new bad data without bricking existing databases.

### 5. Blank `action_type` accepted (medium)

`idempotency_key` already refused a blank type, but only on the branch where no
explicit `key` is supplied, so passing a key bypassed the check. The type is the
unit the retry budget counts and the key the reconciler registry matches on, so a
blank one is silently exempt from both: it matches no probe and pools every
unnamed action into a single budget.

**Fixed.** Validated on both branches.

### 6. Confirming an effect erased its receipt (high)

`reconcile(occurred=True)` rewrote `external_id` from its argument
unconditionally. Omitting it erased a receipt already on record, so a caller
confirming an effect happened, without having captured its id, destroyed the
evidence proving it did. Reproduced live: `receipt-mirror-999` became `null`
while the status stayed `completed`.

**Fixed.** Any recorded `external_id` and `result` survive omission; a caller
passing replacements still overrides them.

Issue #29 is deliberately untouched. `occurred=False` still clears `external_id`
and `result`, because evidence of a completion the system has just decided never
happened is worse than no evidence. Its test passes unchanged.

### 7. Withdrawn: `request_human` on MCP runs (issue #306)

Reported as a regression of #35 and #84. It is neither.
`tests/test_provenance.py::test_an_agent_cannot_certify_its_own_fabricated_progress`
asserts precisely this behaviour, and the reason is concrete: self-reported
progress decides what work a resumed session skips, so an agent that inflates
`completed` to 9999/10000, or is prompt-injected into it, would cause 9999 units
of real work to be silently skipped.

The real defect was discoverability. The status reads as a hard stop, and the
obvious next move, `continuum_confirm`, is refused by design, leaving no legal way
forward.

**Addressed without weakening anything.** The MCP `instructions` field now carries
the session-start protocol and the `request_human` semantics, and `resume` returns
`self_report_guidance` when self-report is the only thing blocking. `CLAUDE.md` was
deleted, since everything it specified now travels with the server.

Issue #306 was corrected publicly and closed as not-a-bug.

## Guarantees confirmed unchanged

Fixing the above must not loosen anything. Each of these was asserted explicitly
after every change.

| Property | Confirmed |
|---|---|
| A self-certified run still resumes as `request_human`, `safe: false` | yes |
| `continuum_confirm` still refuses without `CONTINUUM_MCP_CONFIRM_TOKEN` | yes |
| An uncertain side effect is never re-proposed | yes |
| A fresh identity is still refused once the budget is genuinely exhausted | yes |
| Deduplication by key still ignores argument formatting | yes |
| Drift detection still reports `v3 -> v4` as conflicted | yes |
| `reconcile(occurred=false)` still clears falsified evidence (#29) | yes |
| A certainly-failed action is still retryable | yes |
| Unknown runs never report success on any tool | yes |
| Event chain integrity verified after every run | yes |

## Notes for operators

**A code change needs a server restart.** The MCP server is a long-running
process. Edits to `src/` do not take effect in an existing session even with an
editable install. Confirmed by observing the pre-fix message from the running
server while the patched code was already on disk. Reconnect the client, then
re-verify.

**`.continuum/budgets.json` is absent by default**, so `default_max_attempts` of
3 applies to every action type. With finding 1 fixed this no longer caps distinct
work, but a workflow that genuinely retries more than three times per type still
needs the registry.

**Legacy blank-id rows.** A database written before finding 4 may contain a run
with a blank id. It remains readable and can be closed with
`continuum complete ""`. It will keep winning `get_active_run` until closed.

## Reproducing

```sh
python -m pytest                  # full suite
ruff check . && ruff format --check .
mypy src

# targeted regressions for the findings above
python -m pytest tests/test_retry_budgets.py tests/test_action_ledger.py \
                 tests/test_validator.py tests/test_mcp_server.py -q

# the security properties that must not move
python -m pytest tests/test_provenance.py tests/test_toy_task_banner_attack.py \
                 tests/test_trust_gate.py -q
```

## Known gaps

Stated plainly rather than left implied.

- **Model drift over MCP is still undetectable.** Finding 3 removes the false
  assurance but adds no write path for the model. Issue #308 remains open for
  that decision.
- **No concurrency testing.** Every probe was sequential. Two clients claiming the
  same key simultaneously, or two servers on one SQLite file, are untested here.
- **No Postgres run.** `require_usable_run_id` is wired into the Postgres backend
  but only the SQLite path was executed; the Postgres contract tests need a live
  server.
- **Transient flakiness observed once.** One run reported 2 errors that did not
  reproduce across three subsequent runs. A concurrent process was writing to the
  working tree at the time, which is the likeliest cause, but it was not root
  caused.
- **Dashboard, gateway and compaction** were not exercised. Scope was the MCP tool
  surface.
