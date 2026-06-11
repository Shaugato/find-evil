"""Diamond Model relationship graph on the blackboard (FOR578).

Builds adversary / capability / infrastructure / victim vertices from
ledger findings (+ optional CTI attribution) and stores the graph as JSON
under the Valkey key ``cti:diamond:graph`` so the MCP blackboard exposes it
at ``bb://cti/diamond``.
"""

from __future__ import annotations

import json
import time
from typing import Any

DIAMOND_KEY = "cti:diamond:graph"

_INFRA_PREFIXES = ("ip:", "domain:", "hash:", "url:")


def _node(nid: str, kind: str, label: str) -> dict[str, Any]:
    return {"id": nid, "kind": kind, "label": label}


def build_diamond_graph(
    ledger_rows: list[dict[str, Any]],
    *,
    adversary_label: str = "unattributed",
) -> dict[str, Any]:
    """Pure transform: ledger rows → Diamond Model nodes/edges."""
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    adv_id = f"adversary:{adversary_label}"
    nodes[adv_id] = _node(adv_id, "adversary", adversary_label)

    for row in ledger_rows:
        entry = row.get("entry", {})
        finding_id = str(row.get("finding_id", ""))
        host = str(entry.get("host_id", "")) or "unknown-host"
        victim_id = f"victim:{host}"
        nodes.setdefault(victim_id, _node(victim_id, "victim", host))

        artifact = str(entry.get("primary_artifact_key", ""))
        infra_ids: list[str] = []
        if artifact.startswith(_INFRA_PREFIXES):
            infra_id = f"infrastructure:{artifact}"
            nodes.setdefault(infra_id, _node(infra_id, "infrastructure", artifact))
            infra_ids.append(infra_id)

        cap_ids: list[str] = []
        for tech in entry.get("mitre_attack_technique", []) or []:
            cap_id = f"capability:{tech}"
            nodes.setdefault(cap_id, _node(cap_id, "capability", tech))
            cap_ids.append(cap_id)

        # Diamond edges for this finding: adversary→capability→victim, with
        # infrastructure linked to both capability and victim when present.
        for cap_id in cap_ids:
            edges.append({"src": adv_id, "dst": cap_id, "finding_id": finding_id})
            edges.append({"src": cap_id, "dst": victim_id, "finding_id": finding_id})
        for infra_id in infra_ids:
            edges.append({"src": adv_id, "dst": infra_id, "finding_id": finding_id})
            edges.append({"src": infra_id, "dst": victim_id, "finding_id": finding_id})
            for cap_id in cap_ids:
                edges.append({"src": cap_id, "dst": infra_id, "finding_id": finding_id})

    return {
        "model": "diamond",
        "generated_ns": time.time_ns(),
        "nodes": list(nodes.values()),
        "edges": edges,
        "counts": {
            "adversary": sum(1 for n in nodes.values() if n["kind"] == "adversary"),
            "capability": sum(1 for n in nodes.values() if n["kind"] == "capability"),
            "infrastructure": sum(
                1 for n in nodes.values() if n["kind"] == "infrastructure"
            ),
            "victim": sum(1 for n in nodes.values() if n["kind"] == "victim"),
            "edges": len(edges),
        },
    }


async def refresh_diamond_graph(n_recent: int = 200) -> dict[str, Any]:
    """Rebuild from the latest ledger findings and publish to the blackboard."""
    import asyncio

    from findevil.ledger.reader import LedgerReader
    from findevil.transport.valkey import get_valkey

    def _read() -> list[dict[str, Any]]:
        reader = LedgerReader()
        try:
            return asyncio.run(reader.recent(n_recent))
        finally:
            reader.close()

    rows = await asyncio.to_thread(_read)
    graph = build_diamond_graph(rows)
    vc = await get_valkey()
    c = await vc._connect()  # noqa: SLF001 - raw set for a JSON document key
    await c.set(DIAMOND_KEY, json.dumps(graph))
    return graph
