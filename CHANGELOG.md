# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- 60 additional tests (117 total), 100% line coverage of `src/continuum`.

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
