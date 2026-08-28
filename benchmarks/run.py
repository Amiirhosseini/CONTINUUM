"""Run the Phase 6 recovery-correctness scenario suite and emit a report.

Usage:
    uv run python benchmarks/run.py

Writes ``benchmarks/out/report.json`` and ``benchmarks/out/report.md``. The run
is reproducible: scenarios build their own in-memory state, so the output can be
diffed across commits to watch recovery guarantees hold.

Also runs the fault-injection chaos suite (#397) and emits its report
via the shared emitter schema coordinated with #398 (horizon).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure benchmarks is importable when run as `python benchmarks/run.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from continuum.benchmark.phase6 import run_benchmark, scenarios, write_report


def main() -> None:
    report = run_benchmark(scenarios.ALL_SCENARIOS)
    out_dir = os.path.join(os.path.dirname(__file__), "out")
    os.makedirs(out_dir, exist_ok=True)
    json_path, md_path = write_report(report, os.path.join(out_dir, "report"))
    summary = report.summary()
    print(
        f"scenarios: {summary['total']}  passed: {summary['passed']}  failed: {summary['failed']}"
    )
    print(f"json: {json_path}")
    print(f"md:   {md_path}")

    # Fault-injection chaos suite (#397) — shares the emitter schema with #398
    try:
        from benchmarks.fault_injection.emitter import emit_fault_injection_report
        from benchmarks.fault_injection.runner import run_benchmark_suite

        fault_report = run_benchmark_suite()
        fault_json, fault_md = emit_fault_injection_report(
            fault_report, os.path.join(out_dir, "fault_injection_report")
        )
        fault_summary = fault_report.summary()
        print(
            f"fault-injection: {fault_summary['total']} passed={fault_summary['passed']} failed={fault_summary['failed']}"
        )
        print(f"fault json: {fault_json}")
        print(f"fault md:   {fault_md}")
    except Exception as exc:  # noqa: BLE001 - don't let fault suite break phase6
        print(f"fault-injection benchmark failed: {exc}")


if __name__ == "__main__":
    main()
