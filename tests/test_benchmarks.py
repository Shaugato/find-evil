"""Micro-benchmarks (Part 18.4) — pytest-benchmark style.

These do NOT enforce SLO; they record throughput so regressions become visible
in CI logs. Skip gracefully if `pytest-benchmark` isn't installed.
"""

from __future__ import annotations

import pytest


pytest.importorskip("pytest_benchmark")

from findevil.swarm.ds_fusion import AgentReport, fuse  # noqa: E402


def test_bench_fuse_3_reports(benchmark):
    reports = [
        AgentReport("a", 0.8, 1.0),
        AgentReport("b", 0.7, 1.0),
        AgentReport("c", 0.6, 1.0),
    ]
    out = benchmark(fuse, reports)
    assert "belief_evil" in out
