"""Scoped prompt builder — ensures exhibit_ids get derived deterministically."""

from __future__ import annotations

from findevil.fractal.scoped_prompt import build_scoped_prompt, make_exhibits


def test_exhibit_ids_stable():
    items = [{"path": "/x/y", "sha256": "a" * 64}]
    a = make_exhibits(items)
    b = make_exhibits(items)
    assert a[0]["exhibit_id"] == b[0]["exhibit_id"]
    assert a[0]["exhibit_id"].startswith("ex_")


def test_scoped_prompt_mentions_technique():
    frame = {"pher_key": "pher:ip:203.0.113.5", "belief_evil": 0.7, "conflict_K": 0.2}
    p = build_scoped_prompt(frame, exhibits=[{"x": 1}], seed_technique="T1059.001")
    assert "T1059.001" in p
    assert "pher:ip:203.0.113.5" in p


def test_scoped_prompt_forbids_invention():
    p = build_scoped_prompt({"pher_key": "k"}, exhibits=[], seed_technique=None)
    assert "NEVER invent" in p
