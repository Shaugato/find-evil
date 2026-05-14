"""Threshold evaluator bucket tests."""

from __future__ import annotations

from findevil.swarm.ds_fusion import AgentReport
from findevil.swarm.evaluator import evaluate


def test_mitigate_requires_diversity_and_belief():
    reports = [AgentReport("a", 0.95, 1.0), AgentReport("b", 0.9, 1.0)]
    out = evaluate(reports, pheromone_tau=5.0, sensor_diversity=3)
    assert out["action"] == "mitigate"


def test_low_diversity_blocks_mitigate():
    reports = [AgentReport("a", 0.95, 1.0)]
    out = evaluate(reports, pheromone_tau=5.0, sensor_diversity=1)
    assert out["action"] in ("observe", "conflict_ledger", "escalate_human")


def test_high_conflict_escalates():
    reports = [
        AgentReport("a", 1.0, 1.0),
        AgentReport("b", 0.0, 1.0),
    ]
    out = evaluate(reports, pheromone_tau=0.0, sensor_diversity=2)
    assert out["action"] == "escalate_human"


def test_default_observe_when_quiet():
    reports = [AgentReport("a", 0.1, 1.0)]
    out = evaluate(reports, pheromone_tau=0.0, sensor_diversity=1)
    assert out["action"] == "observe"
