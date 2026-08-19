"""CONTINUUM-Bench: the results must be real, never invented.

These tests run the actual library (storage, checkpointing, validation,
recovery, action ledger) and assert the measured numbers show what the docs
claim: CONTINUUM avoids duplicate work and duplicate side effects where the
naive baselines do not.
"""

from __future__ import annotations

from continuum.benchmark import (
    METHODS,
    SCENARIOS,
    IdempotencyResult,
    MethodResult,
    run_benchmark,
    run_idempotency_benchmark,
)


def test_recovery_benchmark_covers_every_scenario_and_method() -> None:
    results = run_benchmark(total=20)
    assert len(results) == len(SCENARIOS) * len(METHODS)
    assert {r.method for r in results} == set(METHODS)
    assert {r.scenario for r in results} == set(SCENARIOS)


def test_continuum_recovers_without_duplicate_work() -> None:
    results = {r.scenario: {} for r in run_benchmark(total=40)}  # type: ignore[var-annotated]
    for r in run_benchmark(total=40):
        results[r.scenario][r.method] = r
    for scenario in SCENARIOS:
        cont = results[scenario]["continuum"]
        assert isinstance(cont, MethodResult)
        assert cont.duplicate_work_ratio == 0.0
        assert cont.duplicate_side_effects == 0
        # CONTINUUM must notice a changed environment; naive baselines are blind.
        if SCENARIOS[scenario].env_change:
            assert cont.detected_stale is True


def test_idempotency_benchmark_proves_issue_6() -> None:
    total = 50
    results = {r.method: r for r in run_idempotency_benchmark(total=total)}
    assert set(results) == {
        "continuum_key",
        "continuum_drift",
        "naive_retry",
        "replay",
    }

    # CONTINUUM dedups across argument shape changes (absolute vs relative path).
    for method in ("continuum_key", "continuum_drift"):
        r = results[method]
        assert isinstance(r, IdempotencyResult)
        assert r.attempts == total
        assert r.distinct_side_effects == total
        assert r.duplicate_side_effects == 0

    # Baselines repeat the side effect on every retry.
    for method in ("naive_retry", "replay"):
        r = results[method]
        assert r.attempts == 2 * total
        assert r.duplicate_side_effects == total
