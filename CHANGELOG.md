# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — Phase 6: action ledger and idempotency

- Idempotency keys (`continuum.actions.idempotency`) derived from action type plus canonically
  hashed arguments, so argument order never matters but a changed value always does. `scope`
  separates runs; `volatile` excludes fields like retry counters that would otherwise make every
  retry look like a new action. Nothing is excluded by default — collapsing two genuinely different
  operations into one would silently skip real work.
- `ActionLedger` (`continuum.actions.ledger`) implementing claim -> perform -> complete, stored as
  events so it inherits the log's ordering, durability and tamper-evidence. A repeat claim for a
  completed action returns the stored result and external id instead of performing it again.
- **`UnknownSideEffect` instead of a guess.** When a crash lands between the effect and its record,
  the ledger cannot tell whether it happened, and neither retrying nor skipping is safe by default.
  It raises and requires reconciliation. Every crash interleaving is enumerated in the module
  docstring.
- A timeout is treated as uncertainty, not absence: `fail(..., certain=False)` records `UNKNOWN`
  rather than `FAILED`, because a request that timed out may still have been processed.
- Reconciliation strategies (`continuum.actions.reconciliation`): `ProbeReconciler` (ask the
  external system — the only strategy producing evidence), `AssumeNotOccurredReconciler` (requires
  explicitly asserting `idempotent=True`), and `ManualReconciler` (escalates). A probe that raises
  is treated as "could not determine", never as evidence of absence. There is deliberately no
  `AssumeOccurred` strategy: assuming success without evidence silently drops work, and a dropped
  side effect is invisible.
- Per-action-type reconciler mapping, so a file upload can be retried while a payment escalates.
- 46 new tests (375 total), including three real-subprocess tests that crash after performing a
  side effect and assert the external system ends with exactly one record. 100% line coverage.

### Fixed

- `SQLiteStorage` now closes its connection on finalisation, so a dropped handle does not leak a
  file descriptor. Documented as a safety net, not a substitute for `close()`.

### Added — Phase 5: state validation

- Environment capture (`continuum.environment.snapshot`): pluggable `EnvironmentProvider` with
  `StaticProvider`, `FileProvider` (content hashes, so touching a file does not invalidate work),
  `ValueProvider` and `CallableProvider`. Providers never raise — a resource that cannot be
  inspected is recorded as `UNKNOWN_VERSION`, because an environment check that fails open defeats
  the purpose of checking.
- Environment diffing (`continuum.environment.diff`) distinguishing `UNCHANGED`, `CHANGED`, `ADDED`,
  `REMOVED` and `UNKNOWN`. `UNKNOWN` is not a softer `UNCHANGED`: an unverifiable resource is
  treated as breaking, so uncertainty degrades rather than resolves in the system's favour. Adding a
  resource is explicitly non-breaking; checksums outrank version labels as identity.
- `StateValidator` (`continuum.state.validator`) checking every component against the environment as
  it is *now*, and returning a `ValidationOutcome` whose `state` already carries the revised
  statuses so callers need not re-derive them.
- **Staleness propagation** along `dependency -> evidence -> finding -> decision`. A dataset moving
  v3 to v4 does not only invalidate the dependency; it invalidates the reasoning built on it.
  Marking only the dependency would leave an agent reasoning from conclusions it can no longer
  justify. State that did not depend on the change is left untouched.
- Approval expiry (by status and by timestamp), model-switch detection that never assumes switching
  is safe, and detection of state citing support it cannot produce.
- `strict_unknown` (default on) decides whether unverifiable resources block a clean resume.
- 52 new tests (329 total), 100% line coverage maintained.

### Fixed

- `SemanticState.dangling_evidence()` reported a false alarm for any decision citing a *finding*
  rather than raw evidence — which is legitimate provenance and occurs in every well-formed
  reasoning chain. Findings now count as citable support. False alarms are how real ones get
  ignored.

### Removed

- A dead branch in progress validation that re-checked a counter invariant the `Progress` model
  already enforces on construction and deserialization. Verified unreachable rather than left as
  untestable code; the invariant is tested at the model level.

### Added — Phase 4: checkpoint creation

- Checkpoint policies (`continuum.checkpoint.policy`): `ManualPolicy`, `IntervalPolicy`,
  `EventPolicy`, `SemanticPolicy`, `ContextPressurePolicy` and `HybridPolicy`, plus a
  `default_policy()` that checks explicit requests, side effects and meaning before falling back to
  time — so a checkpoint reports the real reason it was taken rather than "the timer went off".
  Policies are pure functions of an explicit `PolicyContext`, including the clock, which makes
  checkpoint timing testable instead of flaky.
- `SemanticPolicy` fires on meaning, not volume: structural changes (a decision recorded or
  invalidated, a dependency version change, an approval, a model switch) always checkpoint, while
  incremental progress only checkpoints on crossing a configurable stride.
- `CheckpointManager` (`continuum.checkpoint.manager`): evaluates policy, projects state, writes
  version then checkpoint then annotation, and restores. The write ordering is documented against
  each crash interleaving; no ordering can produce a checkpoint that claims to cover events it does
  not.
- `restore()` replays events recorded after the checkpoint onto it, so a crash *between* checkpoints
  does not discard the work in between. `replay=False` returns the checkpoint on its own terms for
  validators that must judge it before trusting anything newer.
- Bounded recovery context (`continuum.checkpoint.context`): renders the minimum sufficient briefing
  — goal, verified progress, stale state, items requiring review, valid decisions, pending work,
  findings ranked by confidence, dependencies. Sections drop from the least important end under a
  token budget, but goal, progress and stale state are never dropped: an agent that resumes without
  knowing what to distrust is worse than one that does not resume.
- Token counts are explicitly labelled heuristic estimates (character-based). CONTINUUM takes no
  tokenizer dependency, and no compression ratio is claimed until the benchmark measures one.
- 71 new tests (277 total), 100% line coverage maintained.

### Fixed

- A checkpoint's own `STATE_CHECKPOINTED` annotation was counted as unreplayed work, so every
  freshly-checkpointed run looked stale and restore replayed a no-op event each time. The manager
  now advances the cursor past its own annotation, with a fallback for the crash interleaving where
  the annotation was never written.

### Added — Phase 3: SQLite persistence

- `Storage` interface (`continuum.storage.base`) covering runs, events, state versions and
  checkpoints, with its guarantees and non-guarantees documented in the module itself: append-only
  events, atomic sequence allocation and durability on commit are promised; exactly-once,
  distribution and encryption at rest explicitly are not.
- `SQLiteStorage` (`continuum.storage.sqlite`): WAL journaling so readers never block the writer,
  `synchronous=FULL` so committed work survives power loss, enforced foreign keys, `IMMEDIATE`
  write transactions, and a `UNIQUE(run_id, sequence)` backstop that turns a write race into a
  `ConcurrentWriteError` instead of a silently forked chain.
- Optimistic concurrency via `expected_sequence`, letting a caller detect that a run moved on
  beneath it rather than blindly appending.
- `verify_events` re-audits a persisted chain directly from SQL, reporting `trusted_through` and
  flagging unreadable rows without raising.
- Integrity on read: corrupted runs, versions and checkpoints raise `CorruptedRecord` rather than
  returning untrustworthy state. Checkpoints are sealed with an integrity hash on write.
- `Run` model and sealed `StateCheckpoint` (`content`/`digest`/`sealed`/`verify`).
- `open_storage()` URL handling for `sqlite:///path`, bare paths and `:memory:`; PostgreSQL fails
  with a clear `NotImplementedError` instead of silently falling back to a local file.
- 65 new tests (206 total), including two OS processes racing on one database file and a hard
  `os._exit` mid-run, verified to resume with zero duplicated work.

### Fixed

- Event payloads are now validated as JSON-native at construction. A `datetime` in a payload hashed
  one way in memory and another way after being read back, which would have made a valid event fail
  reload — phantom corruption caused by storage, not by tampering.
- `sqlite://` URL parsing no longer strips the leading slash of an absolute path, which had caused
  the database to be created in the working directory instead of the requested location.

### Added — Phase 2: semantic state representation

- Deterministic projection (`continuum.state.semantic`): folds an event prefix into `SemanticState`.
  Guarantees reproducibility (no wall-clock dependence) and prefix-closure, so a run can be recovered
  up to the log's `trusted_through` boundary. Unknown event types are counted and reported rather
  than raising, keeping forward-written logs recoverable.
- `Provenance` and `Origin` on every state component: each item traces back to the event that
  produced it, and `reproducible` distinguishes re-derivable state from asserted or inferred state.
- Pluggable extraction (`continuum.state.extractor`): `StateExtractor` protocol,
  `DeterministicExtractor` (no model, no network), optional `LLMExtractor` that may only add
  components — never modify or delete recorded facts — tagging everything `Origin.LLM` and
  `REQUIRES_REVIEW`, and degrading to the deterministic result if the callable raises.
  `CompositeExtractor` chains extractors without double-applying events.
- Content-addressed version chain (`continuum.state.versioning`): linked, verifiable history that
  refuses to record semantically unchanged states.
- Semantic diff (`continuum.state.diff`): ID-based comparison that ignores reordering, separates
  `INVALIDATED` from `CHANGED`, produces deterministic output, and renders for the CLI.
- 11 new event types: findings, work, dependencies, approvals and model identity.
- `SemanticState` accessors used by validation and recovery, including `dangling_evidence()` for
  detecting state that cites support it cannot produce.
- 84 additional tests (141 total), 100% line coverage of `src/continuum`.

### Added — Phase 1: data models and event system

- Durable data model (`continuum.models`): semantic state tree (goal, plan, progress, decisions,
  findings, evidence, pending work, approvals, external dependencies, model state), action ledger
  records, environment snapshots, validation reports, recovery contracts, checkpoints and diffs.
- Status vocabularies as `StrEnum`: `StateStatus`, `ActionStatus`, `RunStatus`, `ApprovalStatus`,
  `RecoveryMode`, `RecoverySafety`, `Component`, `DiffKind`, `PlanStepStatus`.
- Append-only, hash-chained event log (`continuum.events`) with per-run sequencing, sealed events,
  chain reload validation and an integrity audit reporting `trusted_through` per run.
- Deterministic canonical hashing (`continuum.security.hashing`) with sorted keys, UTC-normalised
  timestamps, enum-by-value serialization, and explicit rejection of non-finite floats, sets and
  ambiguous mapping keys.
- Test suite: 57 tests covering model invariants, immutability, serialization determinism, chain
  linkage, tamper/deletion/fork detection and property-based version monotonicity.

### Notes

- No runtime, storage engine, validator, ledger logic, recovery engine or CLI yet.
- No benchmark results are claimed; the harness does not exist.
