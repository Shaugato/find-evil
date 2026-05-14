"""LangGraph multi-agent debate for H2 (blueprint Part 10).

Graph:

    START -> prosecutor -> defense -> judge -> END

Prosecutor and defense both receive the exhibit list + the prior-side argument.
Judge sees both arguments (optionally swapped for position-bias mitigation) and
returns a Verdict. Everything is outlines-schema-constrained via the
`InferenceFacade`.

This graph is NOT on the hot path; it is invoked out-of-band when the swarm
produces a `conflict_ledger` or `escalate_human` action.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, TypedDict

from findevil.inference.facade import InferenceFacade
from findevil.inference.outlines_schemas import (
    DebateArgument,
    Verdict,
    allowed_exhibit_ids,
    validate_argument_citations,
    validate_verdict_citations,
)
from findevil.observability.logging import get_logger
from findevil.observability.metrics import INFERENCE_LATENCY, NARRATOR_DEBATES

log = get_logger("findevil.narrator.graph")


class _State(TypedDict, total=False):
    exhibits: list[dict[str, Any]]
    prosecutor_arg: DebateArgument | None
    defense_arg: DebateArgument | None
    verdict: Verdict | None
    swap_judge: bool
    started_ns: int
    finished_ns: int


@dataclass
class NarratorGraph:
    """Compiled LangGraph with pinned InferenceFacade — instantiate once per worker."""

    facade: InferenceFacade = field(default_factory=InferenceFacade)
    graph: Any = field(init=False)

    def __post_init__(self):
        self.graph = build_graph(self.facade)

    async def debate(
        self, exhibits: list[dict[str, Any]], *, swap_judge: bool = False
    ) -> dict[str, Any]:
        """Run a debate end-to-end and return dict payload {arguments, verdict}."""
        state: _State = {
            "exhibits": exhibits,
            "swap_judge": swap_judge,
            "started_ns": time.time_ns(),
        }
        out = await self.graph.ainvoke(state)
        v = out.get("verdict")
        if v is not None and isinstance(v, Verdict):
            NARRATOR_DEBATES.labels(
                verdict="evil" if v.guilty else "benign"
            ).inc()
        return {
            "prosecutor": (
                out.get("prosecutor_arg").model_dump()
                if out.get("prosecutor_arg") is not None
                else None
            ),
            "defense": (
                out.get("defense_arg").model_dump()
                if out.get("defense_arg") is not None
                else None
            ),
            "verdict": v.model_dump() if v is not None else None,
            "started_ns": out.get("started_ns"),
            "finished_ns": out.get("finished_ns"),
        }


def build_graph(facade: InferenceFacade):
    """Build (and compile) the LangGraph StateGraph."""
    from langgraph.graph import END, START, StateGraph

    async def prosecutor(state: _State) -> _State:
        t0 = time.perf_counter_ns()
        arg = await facade.debate_argument(
            role="prosecutor", exhibits=state.get("exhibits", []), prior=""
        )
        validate_argument_citations(arg, state.get("exhibits", []))
        INFERENCE_LATENCY.labels(role="prosecutor").observe(
            (time.perf_counter_ns() - t0) / 1e9
        )
        return {"prosecutor_arg": arg}

    async def defense(state: _State) -> _State:
        prior = (
            state["prosecutor_arg"].text
            if state.get("prosecutor_arg") is not None
            else ""
        )
        t0 = time.perf_counter_ns()
        arg = await facade.debate_argument(
            role="defense", exhibits=state.get("exhibits", []), prior=prior
        )
        validate_argument_citations(arg, state.get("exhibits", []))
        INFERENCE_LATENCY.labels(role="defense").observe(
            (time.perf_counter_ns() - t0) / 1e9
        )
        return {"defense_arg": arg}

    async def judge(state: _State) -> _State:
        p = state.get("prosecutor_arg")
        d = state.get("defense_arg")
        if p is None or d is None:
            return {"finished_ns": time.time_ns()}
        t0 = time.perf_counter_ns()
        exhibits = state.get("exhibits", [])
        allowed = allowed_exhibit_ids(exhibits)
        v = await facade.judge_verdict(
            exhibits=exhibits,
            prosecutor=p.text,
            defense=d.text,
            swap=False,
        )
        validate_verdict_citations(v, exhibits)
        if bool(state.get("swap_judge", False)):
            swapped_verdict = await facade.judge_verdict(
                exhibits=exhibits,
                prosecutor=p.text,
                defense=d.text,
                swap=True,
            )
            validate_verdict_citations(swapped_verdict, exhibits)
            if swapped_verdict.score >= v.score:
                v = swapped_verdict
        if any(exhibit_id not in allowed for exhibit_id in v.exhibit_ids_cited):
            raise ValueError("fabricated exhibit_id in judge verdict")
        INFERENCE_LATENCY.labels(role="judge").observe(
            (time.perf_counter_ns() - t0) / 1e9
        )
        return {"verdict": v, "finished_ns": time.time_ns()}

    g = StateGraph(_State)
    g.add_node("prosecutor", prosecutor)
    g.add_node("defense", defense)
    g.add_node("judge", judge)
    g.add_edge(START, "prosecutor")
    g.add_edge("prosecutor", "defense")
    g.add_edge("defense", "judge")
    g.add_edge("judge", END)
    return g.compile()
