"""Run the Phase 6 recovery-correctness scenario suite and emit a report.

Usage:
    uv run python benchmarks/run.py

Writes ``benchmarks/out/report.json`` and ``benchmarks/out/report.md``. The run
is reproducible: scenarios build their own in-memory state, so the output can be
diffed across commits to watch recovery guarantees hold.
"""

from __future__ import annotations

import os

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


if __name__ == "__main__":
    main()
