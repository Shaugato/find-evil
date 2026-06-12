"""Truncated-JSON repair for small-model debate output (facade)."""

from __future__ import annotations

import json

from findevil.inference.facade import _repair_truncated_json


def test_repairs_unterminated_string():
    # Model hit max_tokens mid-string.
    bad = '{"role": "prosecutor", "text": "The endpoint shows beacon'
    fixed = _repair_truncated_json(bad)
    obj = json.loads(fixed)
    assert obj["role"] == "prosecutor"
    assert obj["text"].startswith("The endpoint shows beacon")


def test_repairs_open_array_and_object():
    bad = '{"role": "judge", "exhibit_ids_cited": ["ex-1", "ex-2"'
    obj = json.loads(_repair_truncated_json(bad))
    assert obj["exhibit_ids_cited"] == ["ex-1", "ex-2"]


def test_drops_dangling_key():
    bad = '{"score": 0.4, "winning_argument": "defense", "rationale"'
    obj = json.loads(_repair_truncated_json(bad))
    assert obj["score"] == 0.4
    assert obj["winning_argument"] == "defense"


def test_complete_json_unchanged():
    good = '{"a": 1, "b": [2, 3], "c": "ok"}'
    assert json.loads(_repair_truncated_json(good)) == {"a": 1, "b": [2, 3], "c": "ok"}
