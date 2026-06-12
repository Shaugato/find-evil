"""Zheng-2023 position-swap (doc Part 10.2) — both judge orderings must run."""

from __future__ import annotations

import asyncio

import pytest

from findevil.inference.outlines_schemas import DebateArgument, Verdict
from findevil.narrator.graph import NarratorGraph


class _FakeFacade:
    """Records every judge call's swap flag; returns canned schema objects."""

    def __init__(self):
        self.judge_swaps: list[bool] = []

    async def debate_argument(self, role: str, exhibits, prior: str = "") -> DebateArgument:
        return DebateArgument(
            role=role,
            text=f"{role} canned argument",
            exhibit_ids_cited=[exhibits[0]["exhibit_id"]] if exhibits else [],
        )

    async def judge_verdict(self, exhibits, prosecutor: str, defense: str, *, swap: bool = False) -> Verdict:
        self.judge_swaps.append(swap)
        return Verdict(
            guilty=False,
            score=0.4 if swap else 0.3,
            winning_argument="insufficient",
            rationale="canned",
            exhibit_ids_cited=[],
        )


EXHIBITS = [{"exhibit_id": "ex-1", "exhibit_kind": "pheromone_state", "tau": 0.4}]


def test_swap_judge_runs_both_orderings():
    facade = _FakeFacade()
    ng = NarratorGraph(facade=facade)  # type: ignore[arg-type]
    out = asyncio.run(ng.debate(exhibits=EXHIBITS, swap_judge=True))
    assert facade.judge_swaps == [False, True], facade.judge_swaps
    # Higher-scoring (swapped) verdict wins per graph policy.
    assert out["verdict"]["score"] == pytest.approx(0.4)


def test_swap_disabled_runs_single_ordering():
    facade = _FakeFacade()
    ng = NarratorGraph(facade=facade)  # type: ignore[arg-type]
    asyncio.run(ng.debate(exhibits=EXHIBITS, swap_judge=False))
    assert facade.judge_swaps == [False]


def test_production_default_enables_swap(monkeypatch):
    monkeypatch.delenv("FINDEVIL_NARRATOR_SWAP_JUDGE", raising=False)
    import importlib

    from findevil.narrator import service as nsvc

    importlib.reload(nsvc)
    assert nsvc._SWAP_JUDGE is True  # noqa: SLF001
