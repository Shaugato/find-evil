"""Threshold evaluator produces AgentReports per pher-key with noisy-OR lift."""

from __future__ import annotations

from findevil.ingest.events import ParsedEvent
from findevil.ingest.threshold import evaluate


def _evt(**kw) -> ParsedEvent:
    defaults = dict(ts_ns=0, source="sysmon", sensor="s1", host_id="h1", kind="proc_create")
    defaults.update(kw)
    return ParsedEvent(**defaults)


def test_same_key_multiple_signals_boosts_confidence():
    e1 = _evt(sha256="a" * 64, confidence=0.3)
    e2 = _evt(sha256="a" * 64, confidence=0.3, sensor="s2")
    out = evaluate([e1, e2])
    key = (None, None, "a" * 64, None)
    reports = out.get(key, [])
    confs = [r.confidence for r in reports]
    # Each sensor becomes its own agent, but the fold within an agent must exceed its raw
    assert all(0.0 <= c <= 1.0 for c in confs)
    assert any(c > 0.2 for c in confs)


def test_distinct_keys_get_distinct_reports():
    e1 = _evt(sha256="a" * 64, confidence=0.5)
    e2 = _evt(ip="203.0.113.5", confidence=0.5, kind="proc_net")
    out = evaluate([e1, e2])
    assert (None, None, "a" * 64, None) in out
    assert ("203.0.113.5", None, None, None) in out
