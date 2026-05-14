"""Arkime / Moloch full-packet search shim — HTTP API backed."""

from __future__ import annotations

from typing import Any

import httpx

from findevil.tools.registry import register

from ._subprocess import first_target


@register("arkime.search")
async def search(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    expr = t.get("expression") or (
        f"ip == {t['value']}" if t.get("type") == "ipv4-addr" and t.get("value") else None
    )
    if not expr:
        return {"ok": False, "error": "missing target.expression"}
    base = t.get("arkime_url", "http://127.0.0.1:8005")
    user = t.get("user", "admin")
    pwd = t.get("password", "admin")
    try:
        async with httpx.AsyncClient(timeout=15.0, auth=(user, pwd)) as cx:
            r = await cx.get(f"{base}/api/sessions", params={"expression": expr, "length": 100})
            r.raise_for_status()
            return {"ok": True, "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
