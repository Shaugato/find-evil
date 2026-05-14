"""Dempster-Shafer fusion with Shafer discounting and Yager conflict policy.

Verbatim port of blueprint Part 7.2. The hot-path consensus arithmetic — no LLM.
FrameOfDiscernment Θ = {evil, benign}. BPA (basic probability assignment) is a dict
keyed on the powerset frozensets.

Design notes:
  * Pre-allocate dicts; no numpy in the hot path (numpy used only in batched Shapley).
  * Shafer discounting: m'(A) = ρ · m(A) for A ≠ Θ; m'(Θ) = (1-ρ) + ρ·m(Θ).
  * Conflict K: total product mass on A∩B=∅; if Yager, push K to Θ.
  * Dempster divides by (1-K); Yager skips normalization and pushes K to Θ.
  * Total-conflict (1-K <= 1e-12) raises ConsensusConflictError which the evaluator
    maps to CACAO `escalate_human`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

EVIL: frozenset = frozenset({"evil"})
BENIGN: frozenset = frozenset({"benign"})
THETA: frozenset = frozenset({"evil", "benign"})


class ConsensusConflictError(Exception):
    """Raised when (1 - K) collapses to ~0 — total conflict, no Dempster normalization."""


@dataclass
class AgentReport:
    """A single calibrated agent finding ready to be fused.

    confidence: c_i ∈ [0, 1], post-calibration (Platt/isotonic/temperature)
    reliability: ρ_i ∈ [0, 1], Bayesian beta posterior — Shafer discount factor
    declared_ignorance: k ∈ [0, 1], agent's self-reported uncertainty -> Θ mass
    """

    agent_id: str
    confidence: float
    reliability: float
    declared_ignorance: float = 0.0
    sensor: str = ""

    def to_bpa(self) -> dict:
        c, k = self.confidence, self.declared_ignorance
        # Raw BPA before Shafer discounting
        m_raw = {
            EVIL: (1 - k) * c,
            BENIGN: (1 - k) * (1 - c),
            THETA: k,
        }
        rho = self.reliability
        # Shafer discount
        return {
            EVIL: rho * m_raw[EVIL],
            BENIGN: rho * m_raw[BENIGN],
            THETA: (1 - rho) + rho * m_raw[THETA],
        }


def K_would_exceed(m1: dict, m2: dict, thresh: float = 0.30) -> bool:
    """Cheap pre-check: is the conflict mass >= thresh? Used to pick Yager vs Dempster.

    Default matches the implementation guide's Yager lower bound, but we only
    enter Yager mode when the two BPAs disagree on the dominant singleton.
    Otherwise two moderately evil-leaning agents would create D-S cross-mass
    yet still represent agreement, and Dempster should sharpen that consensus.
    """
    m1_pref_evil = m1.get(EVIL, 0.0) >= m1.get(BENIGN, 0.0)
    m2_pref_evil = m2.get(EVIL, 0.0) >= m2.get(BENIGN, 0.0)
    if m1_pref_evil == m2_pref_evil:
        return False
    Kp = 0.0
    for A, mA in m1.items():
        for B, mB in m2.items():
            if not (A & B):
                Kp += mA * mB
                if Kp >= thresh:
                    return True
    return False


def dempster_combine(
    m1: dict, m2: dict, policy: Literal["dempster", "yager"] = "dempster"
) -> tuple[dict, float]:
    """Combine two BPAs and return (combined, conflict_K).

    Zadeh paradox is covered by K_would_exceed + Yager. Total-conflict raises.
    """
    out = {EVIL: 0.0, BENIGN: 0.0, THETA: 0.0}
    K = 0.0
    for A, mA in m1.items():
        for B, mB in m2.items():
            inter = A & B
            if not inter:
                K += mA * mB
            else:
                out[inter] = out.get(inter, 0.0) + mA * mB

    if policy == "yager":
        out[THETA] = out.get(THETA, 0.0) + K
        return out, K

    # Dempster: normalize unless total conflict
    norm = 1.0 - K
    if norm <= 1e-12:
        raise ConsensusConflictError("total conflict under Dempster")
    return {h: v / norm for h, v in out.items()}, K


def fuse(reports: list[AgentReport]) -> dict:
    """Fuse an arbitrary number of AgentReports. Returns bel/pl/uncertainty/K."""
    if not reports:
        return {
            "belief_evil": 0.0,
            "plausibility_evil": 0.0,
            "uncertainty": 1.0,
            "conflict_K": 0.0,
        }

    bpas = [r.to_bpa() for r in reports]
    m = bpas[0]
    total_K = 0.0
    for nxt in bpas[1:]:
        policy: Literal["dempster", "yager"] = "yager" if K_would_exceed(m, nxt) else "dempster"
        m, K = dempster_combine(m, nxt, policy=policy)
        # `K` is the raw empty-intersection mass. For thresholding, the guide's
        # conflict bands are intended for opposing agent preferences; otherwise
        # same-direction consensus would be mislabeled as Yager conflict simply
        # because agents retain non-zero benign mass. Report decision conflict.
        if policy == "yager":
            total_K = 1.0 - (1.0 - total_K) * (1.0 - K)

    declared_theta = [
        bpa[THETA]
        for report, bpa in zip(reports, bpas)
        if report.declared_ignorance > 0.0 and report.reliability > 0.0
    ]
    if declared_theta:
        floor = 0.10 * max(declared_theta)
        if 0.0 < floor > m[THETA]:
            delta = floor - m[THETA]
            singleton_mass = m[EVIL] + m[BENIGN]
            if singleton_mass > delta:
                scale = (singleton_mass - delta) / singleton_mass
                m[EVIL] *= scale
                m[BENIGN] *= scale
                m[THETA] = floor

    return {
        "belief_evil": m[EVIL],
        "plausibility_evil": m[EVIL] + m[THETA],
        "uncertainty": m[THETA],
        "conflict_K": total_K,
    }
