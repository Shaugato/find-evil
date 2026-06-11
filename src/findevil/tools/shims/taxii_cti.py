"""CTI MCP tools (FOR578) — TAXII ingest/push + Diamond Model graph."""

from __future__ import annotations

from typing import Any

from findevil.tools.registry import register

from ._subprocess import first_arg, first_target


@register("taxii.ingest")
async def taxii_ingest(commands: list[dict]) -> dict[str, Any]:
    """Ingest CTI indicators as pheromone priors.

    target.bundle_path → offline STIX 2.1 bundle file (default mode), or
    target.api_root + target.collection_id → live TAXII 2.1 poll.
    """
    from findevil.cti.taxii_ingest import ingest_bundle_file, ingest_taxii_collection

    t = first_target(commands)
    bundle_path = t.get("bundle_path") or t.get("value")
    if bundle_path:
        return await ingest_bundle_file(bundle_path)

    api_root = t.get("api_root")
    collection_id = t.get("collection_id")
    if not api_root or not collection_id:
        return {
            "ok": False,
            "error": "need target.bundle_path or target.api_root+collection_id",
        }
    return await ingest_taxii_collection(
        api_root,
        collection_id,
        username=t.get("username"),
        password=t.get("password"),
        added_after=t.get("added_after"),
    )


@register("taxii.push")
async def taxii_push(commands: list[dict]) -> dict[str, Any]:
    """Push a STIX bundle (by ledger seq or inline) to a TAXII 2.1 collection."""
    from findevil.cti.taxii_ingest import push_bundle

    t = first_target(commands)
    api_root = t.get("api_root")
    collection_id = t.get("collection_id")
    if not api_root or not collection_id:
        return {"ok": False, "error": "missing target.api_root or target.collection_id"}

    bundle = first_arg(commands, "bundle")
    if bundle is None:
        from findevil.tools.registry import resolve

        stix_fn = resolve("stix.bundle")
        seq = t.get("seq", -1)
        out = await stix_fn([{"target": {"seq": seq}}])
        if not out.get("ok"):
            return out
        bundle = out["bundle"]
    return await push_bundle(
        api_root,
        collection_id,
        bundle,
        username=t.get("username"),
        password=t.get("password"),
    )


@register("diamond.graph")
async def diamond_graph(commands: list[dict]) -> dict[str, Any]:
    """Rebuild the Diamond Model graph from recent ledger findings."""
    from findevil.cti.diamond import refresh_diamond_graph

    n = int(first_target(commands).get("n", 200))
    try:
        graph = await refresh_diamond_graph(n_recent=n)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"ok": True, "counts": graph["counts"], "key": "cti:diamond:graph"}
