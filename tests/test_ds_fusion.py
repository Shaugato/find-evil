"""Dempster-Shafer math tests (blueprint Part 7.2 / Part 18.2)."""

from __future__ import annotations

import math

import pytest

from findevil.swarm.ds_fusion import (
    AgentReport,
    BENIGN,
    ConsensusConflictError,
    EVIL,
    K_would_exceed,
    THETA,
    dempster_combine,
    fuse,
)


def _approx(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


def test_single_report_evil_heavy():
    r = AgentReport(agent_id="a", confidence=0.9, reliability=1.0, declared_ignorance=0.0)
    res = fuse([r])
    assert _approx(res["belief_evil"], 0.9)
    assert _approx(res["plausibility_evil"], 0.9)
    assert _approx(res["conflict_K"], 0.0)


def test_fuse_two_agreeing_agents_raises_belief():
    r1 = AgentReport("a", 0.7, 1.0)
    r2 = AgentReport("b", 0.7, 1.0)
    res = fuse([r1, r2])
    assert res["belief_evil"] > 0.7  # Dempster sharpens agreement
    assert res["conflict_K"] == 0.0


def test_zadeh_paradox_triggers_yager():
    # Zadeh: c=1 for evil vs c=0 (benign) — total conflict under Dempster.
    r1 = AgentReport("a", 1.0, 1.0)
    r2 = AgentReport("b", 0.0, 1.0)
    res = fuse([r1, r2])
    # Yager pushes conflict to Θ; belief should collapse near zero and uncertainty near 1.
    assert res["conflict_K"] > 0.9
    assert res["uncertainty"] > 0.9


def test_dempster_total_conflict_raises():
    m1 = {EVIL: 1.0, BENIGN: 0.0, THETA: 0.0}
    m2 = {EVIL: 0.0, BENIGN: 1.0, THETA: 0.0}
    with pytest.raises(ConsensusConflictError):
        dempster_combine(m1, m2, policy="dempster")


def test_shafer_discount_preserves_mass():
    r = AgentReport("a", 0.8, 0.5, declared_ignorance=0.1)
    bpa = r.to_bpa()
    total = sum(bpa.values())
    assert _approx(total, 1.0, tol=1e-6)


def test_K_would_exceed_short_circuits():
    m1 = {EVIL: 0.9, BENIGN: 0.0, THETA: 0.1}
    m2 = {EVIL: 0.0, BENIGN: 0.9, THETA: 0.1}
    assert K_would_exceed(m1, m2, thresh=0.5)
    assert not K_would_exceed(m1, m2, thresh=0.99)
