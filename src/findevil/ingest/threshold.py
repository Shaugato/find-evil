"""Threshold evaluator — converts ParsedEvents into AgentReport (blueprint Part 8.4).

For each unique (pher_key, sensor) pair inside a sliding window, we aggregate
evidence into a single confidence score, calibrate via `CalibratorRegistry` (one
sklearn/isotonic model per agent_id), and emit an `AgentReport` that D-S fuse()
consumes downstream.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from .indicators import indicator_tuple

from findevil.swarm.calibrate import registry as _cal_registry
from findevil.swarm.ds_fusion import AgentReport

from .events import ParsedEvent


@dataclass
class AggKey:
    """Pheromone-key identifier. At most ONE ioc dim is populated per key."""

    ip: Optional[str] = None
    domain: Optional[str] = None
    sha256: Optional[str] = None
    proc: Optional[str] = None  # "{host}:{pid}"

    def as_tuple(self):
        return (self.ip, self.domain, self.sha256, self.proc)


def _agg_keys(ev: ParsedEvent) -> list[AggKey]:
    keys: list[AggKey] = []
    direct = indicator_tuple(ev.indicator_key)
    if direct is not None:
        ip, domain, sha256, proc = direct
        return [AggKey(ip=ip, domain=domain, sha256=sha256, proc=proc)]
    if ev.ip:
        keys.append(AggKey(ip=ev.ip))
    if ev.domain:
        keys.append(AggKey(domain=ev.domain))
    if ev.sha256:
        keys.append(AggKey(sha256=ev.sha256))
    if ev.pid is not None and ev.host_id:
        keys.append(AggKey(proc=f"{ev.host_id}:{ev.pid}"))
    return keys


def _agent_id_for(ev: ParsedEvent) -> str:
    # sensor id is the grain of a "reporting agent" for fusion
    return f"{ev.source}/{ev.sensor}"


def evaluate(
    events: Iterable[ParsedEvent],
    *,
    reliability_default: float = 0.8,
) -> dict[tuple, list[AgentReport]]:
    """Group events by (AggKey, agent) and emit one calibrated report per group.

    Returns: { pher_key_tuple → [AgentReport, ...] }.
    The caller feeds the list into `ds_fusion.fuse()`.
    """
    # (key_tuple, agent_id) -> list[confidence]
    buckets: dict[tuple[tuple, str], list[float]] = {}
    sensors: dict[tuple[tuple, str], str] = {}
    declared_ign: dict[tuple[tuple, str], float] = {}

    for ev in events:
        agent = _agent_id_for(ev)
        for k in _agg_keys(ev):
            bk = (k.as_tuple(), agent)
            buckets.setdefault(bk, []).append(ev.confidence)
            sensors[bk] = ev.sensor
            # events with attack_techniques reduce declared ignorance
            di = 0.05 if ev.attack_techniques else 0.15
            declared_ign[bk] = min(declared_ign.get(bk, di), di)

    out: dict[tuple, list[AgentReport]] = {}
    for (key_tuple, agent), confs in buckets.items():
        if not confs:
            continue
        # noisy-OR fold — multiple independent signals boost, bounded by 1.
        p = 1.0
        for c in confs:
            p *= 1.0 - max(0.0, min(1.0, c))
        fused_conf = 1.0 - p
        # per-agent calibration
        cal_conf = _cal_registry().calibrate(agent, fused_conf)
        report = AgentReport(
            agent_id=agent,
            confidence=cal_conf,
            reliability=reliability_default,
            declared_ignorance=declared_ign.get((key_tuple, agent), 0.1),
            sensor=sensors[(key_tuple, agent)],
        )
        out.setdefault(key_tuple, []).append(report)
    return out
