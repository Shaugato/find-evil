"""TAXII 2.1 ingest (FOR578) — poll a collection or load a local bundle.

Online mode uses taxii2-client against any TAXII 2.1 server. Offline mode
ingests a STIX 2.1 bundle JSON file — the default for this air-gap-friendly
platform and for reproducible validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from findevil.observability.logging import get_logger

from .stix_priors import deposit_priors, iocs_from_stix_objects

log = get_logger("findevil.cti.taxii")


async def ingest_bundle_file(path: str | Path) -> dict[str, Any]:
    """Ingest a local STIX 2.1 bundle file into pheromone priors."""
    p = Path(path)
    if not p.is_file():
        return {"ok": False, "error": f"bundle not found: {p}"}
    try:
        bundle = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as exc:
        return {"ok": False, "error": f"bundle parse failed: {exc}"}
    objects = bundle.get("objects", [])
    iocs = iocs_from_stix_objects(objects)
    summary = await deposit_priors(iocs)
    log.info("cti.bundle_ingested", path=str(p), iocs=len(iocs), **{
        k: v for k, v in summary.items() if k != "keys"
    })
    return {"ok": True, "indicators": len(iocs), **summary, "source": str(p)}


async def ingest_taxii_collection(
    api_root_url: str,
    collection_id: str,
    *,
    username: str | None = None,
    password: str | None = None,
    added_after: str | None = None,
) -> dict[str, Any]:
    """Poll a TAXII 2.1 collection and deposit indicator priors."""
    try:
        from taxii2client.v21 import Collection
    except ImportError:
        return {"ok": False, "error": "taxii2-client not installed"}

    import anyio

    def _poll() -> list[dict[str, Any]]:
        coll = Collection(
            f"{api_root_url.rstrip('/')}/collections/{collection_id}/",
            user=username,
            password=password,
        )
        kwargs: dict[str, Any] = {}
        if added_after:
            kwargs["added_after"] = added_after
        envelope = coll.get_objects(**kwargs)
        return envelope.get("objects", [])

    try:
        objects = await anyio.to_thread.run_sync(_poll)
    except Exception as exc:
        return {"ok": False, "error": f"taxii poll failed: {type(exc).__name__}: {exc}"}

    iocs = iocs_from_stix_objects(objects)
    summary = await deposit_priors(iocs)
    log.info(
        "cti.taxii_ingested",
        api_root=api_root_url,
        collection=collection_id,
        iocs=len(iocs),
    )
    return {
        "ok": True,
        "indicators": len(iocs),
        **summary,
        "source": f"taxii://{api_root_url}/{collection_id}",
    }


async def push_bundle(
    api_root_url: str,
    collection_id: str,
    bundle: dict[str, Any],
    *,
    username: str | None = None,
    password: str | None = None,
) -> dict[str, Any]:
    """Push a STIX bundle's objects to a TAXII 2.1 collection (taxii.push)."""
    try:
        from taxii2client.v21 import Collection
    except ImportError:
        return {"ok": False, "error": "taxii2-client not installed"}

    import anyio

    envelope = {"objects": bundle.get("objects", [])}
    if not envelope["objects"]:
        return {"ok": False, "error": "bundle has no objects"}

    def _push() -> Any:
        coll = Collection(
            f"{api_root_url.rstrip('/')}/collections/{collection_id}/",
            user=username,
            password=password,
        )
        return coll.add_objects(envelope)

    try:
        status = await anyio.to_thread.run_sync(_push)
    except Exception as exc:
        return {"ok": False, "error": f"taxii push failed: {type(exc).__name__}: {exc}"}
    return {
        "ok": True,
        "status": getattr(status, "status", "unknown"),
        "success_count": getattr(status, "success_count", None),
    }
