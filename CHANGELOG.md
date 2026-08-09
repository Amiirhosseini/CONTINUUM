# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
