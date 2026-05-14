"""Shapley attribution sanity — efficient, symmetric, sum-to-total.

The real `shapley_attribution(reports)` takes `list[AgentReport]` (not a custom
coalition value function). Here we exercise it with three identical agents and
assert that the attribution sums to the full-coalition fused belief and is
symmetric across agents with equal parameters.
"""

from __future__ import annotations

from findevil.swarm.ds_fusion import AgentReport, fuse
from findevil.swarm.shapley import shapley_attribution


def _three_identical_reports() -> list[AgentReport]:
    return [
        AgentReport(
            agent_id=aid,
            confidence=0.8,
            reliability=0.9,
            declared_ignorance=0.05,
            sensor=aid,
        )
        for aid in ("a", "b", "c")
    ]


def test_exact_sum_equals_full_coalition():
    reports = _three_identical_reports()
    phi = shapley_attribution(reports)
    total_bel = fuse(reports)["belief_evil"]
    assert abs(sum(phi.values()) - total_bel) < 1e-9


def test_symmetric_agents_receive_equal_attribution():
    reports = _three_identical_reports()
    phi = shapley_attribution(reports)
    vals = list(phi.values())
    assert abs(vals[0] - vals[1]) < 1e-9
    assert abs(vals[1] - vals[2]) < 1e-9


def test_dummy_agent_gets_zero():
    """A dummy (reliability 0, confidence 0) contributes no belief and so zero phi."""
    reports = _three_identical_reports()
    reports.append(
        AgentReport(
            agent_id="dummy",
            confidence=0.0,
            reliability=0.0,
            declared_ignorance=1.0,
        )
    )
    phi = shapley_attribution(reports)
    assert abs(phi["dummy"]) < 1e-9


def test_kernel_shap_activates_beyond_six_agents():
    """n > 6 triggers the KernelSHAP surrogate; values must still sum close to total."""
    reports = [
        AgentReport(
            agent_id=f"a{i}",
            confidence=0.7,
            reliability=0.85,
            declared_ignorance=0.05,
        )
        for i in range(7)
    ]
    phi = shapley_attribution(reports)
    total_bel = fuse(reports)["belief_evil"]
    # KernelSHAP is sample-based — tolerate a realistic error envelope.
    assert abs(sum(phi.values()) - total_bel) < 0.05
