"""Threshold evaluator — maps fused BPA to CACAO action.

Per blueprint Part 7.4:
  bel >= theta_mitigate AND sensor_diversity >= min -> `mitigate`
  k_yager_lo <= K < k_yager_hi                      -> `conflict_ledger`
  K >= k_escalate                                   -> `escalate_human`
  otherwise                                         -> `observe`
"""

from __future__ import annotations

from typing import Any

from findevil.config.settings import settings

from .ds_fusion import AgentReport, ConsensusConflictError, fuse


def evaluate(
    reports: list[AgentReport],
    *,
    pheromone_tau: float,
    sensor_diversity: int,
) -> dict[str, Any]:
    try:
        r = fuse(reports)
    except ConsensusConflictError as e:
        return {
            "action": "escalate_human",
            "reason": str(e),
            "belief_evil": 0.0,
            "plausibility_evil": 0.0,
            "uncertainty": 1.0,
            "conflict_K": 1.0,
        }

    bel = r["belief_evil"]
    K = r["conflict_K"]
    action: str
    if (
        bel >= settings.swarm.theta_mitigate
        and sensor_diversity >= settings.swarm.sensor_diversity_min
    ):
        action = "mitigate"
    elif K >= settings.swarm.k_escalate:
        action = "escalate_human"
    elif settings.swarm.k_yager_lo <= K < settings.swarm.k_yager_hi:
        action = "conflict_ledger"
    else:
        action = "observe"

    return {
        "action": action,
        "pheromone_tau": pheromone_tau,
        "sensor_diversity": sensor_diversity,
        **r,
    }
