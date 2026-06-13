"""FastAPI dashboard backend (blueprint Part 15.2).

Serves the "Living Cybernetic Organism" front-end from `static/`. Endpoints fall
into three families:

  * `/api/*`   — one-shot JSON snapshots (ledger tip, recent entries, full
                 pheromone field snapshot, current ATT&CK chain, CACAO instances)
  * `/stream/*` — Server-Sent Events. The four firehose streams are forwarded
                  from Valkey shadow channels; `/stream/ledger` polls SQLite for
                  newly-committed sequences (the ledger writer is sync and does
                  not currently publish to a shadow channel)
  * `/`        — the SPA shell, served as static files

Auth deliberately omitted; the service binds to loopback / UDS only. If exposed
beyond the host, front it with an authenticated reverse proxy.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from findevil.config.settings import settings
from findevil.ledger.reader import LedgerReader
from findevil.transport.valkey import get_valkey

app = FastAPI(title="FIND EVIL — Living Cybernetic Organism")

_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# Cap Valkey calls in the snapshot endpoints — the redis client's default
# connection timeout (30s) would otherwise wedge the dashboard whenever
# Valkey is down. The streams have their own retry loop, so this is just
# for the one-shot JSON endpoints.
_VALKEY_TIMEOUT_S = 1.0


# ---------------------------------------------------------------------------
# SPA shell
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse((_STATIC_DIR / "find-evil.html").read_text(encoding="utf-8"))


@app.get("/organism", response_class=HTMLResponse)
async def organism() -> HTMLResponse:
    return HTMLResponse((_STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/guide", response_class=HTMLResponse)
async def guide() -> HTMLResponse:
    return HTMLResponse((_STATIC_DIR / "guide.html").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# JSON snapshot APIs
# ---------------------------------------------------------------------------


@app.get("/api/ledger/tip")
async def api_ledger_tip() -> dict:
    r = LedgerReader()
    try:
        return await r.tip()
    finally:
        r.close()


@app.get("/api/ledger/recent")
async def api_ledger_recent(n: int = 32) -> JSONResponse:
    n = max(1, min(int(n), 200))
    r = LedgerReader()
    try:
        rows = await r.recent(n)
    finally:
        r.close()
    return JSONResponse(rows)


@app.get("/api/mitre/coverage")
async def api_mitre_coverage() -> JSONResponse:
    """Session-global MITRE technique coverage: technique -> finding count across
    the whole ledger. Backs the dashboard matrix's global view (the client falls
    back to aggregating /api/ledger/recent when this route is unavailable)."""
    r = LedgerReader()
    try:
        rows = await r.recent(100000)
    finally:
        r.close()
    counts: dict[str, int] = {}
    for row in rows:
        e = row.get("entry") or {}
        t = e.get("mitre_attack_technique")
        for x in (t if isinstance(t, list) else ([t] if t else [])):
            if x:
                counts[str(x)] = counts.get(str(x), 0) + 1
    return JSONResponse({"techniques": counts, "total_findings": len(rows)})


@app.get("/api/attack_path")
async def api_attack_path() -> dict:
    try:
        vc = await asyncio.wait_for(get_valkey(), timeout=_VALKEY_TIMEOUT_S)
        state = await asyncio.wait_for(vc.hgetall("attack:current_path"), timeout=_VALKEY_TIMEOUT_S)
    except Exception:
        # Valkey unreachable — return empty so the dashboard renders in demo mode.
        return {"techniques": [], "valkey_available": False}
    d = {
        (k.decode() if isinstance(k, bytes) else k): (
            v.decode() if isinstance(v, bytes) else v
        )
        for k, v in state.items()
    }
    techs = json.loads(d.get("techniques", "[]")) if d else []
    return {"techniques": techs, "valkey_available": True}


@app.get("/api/pher/snapshot")
async def api_pher_snapshot() -> JSONResponse:
    """Full snapshot of the live pheromone field. Used to bootstrap the swarm.

    Returns `{nodes: [], valkey_available: false}` when Valkey is unreachable so
    the front-end can fall back to its synthetic seed without the request 500'ing.
    """
    async def _scan() -> list[dict]:
        rows: list[dict] = []
        vc = await get_valkey()
        async for raw in vc.scan_iter(match="pher:*", count=500):
            key = raw.decode() if isinstance(raw, bytes) else raw
            if key.endswith(":sensors") or ":history" in key:
                continue
            h = await vc.hgetall(key)
            d = {
                (k.decode() if isinstance(k, bytes) else k): (
                    v.decode() if isinstance(v, bytes) else v
                )
                for k, v in h.items()
            }
            try:
                tau = float(d.get("tau", 0.0))
            except ValueError:
                tau = 0.0
            try:
                bel = float(d.get("bel_evil", 0.0))
            except ValueError:
                bel = 0.0
            kind = (
                "ip" if key.startswith("pher:ip:") else
                "hash" if key.startswith("pher:hash:") else
                "domain" if key.startswith("pher:domain:") else
                "process" if key.startswith("pher:proc:") else "unknown"
            )
            rows.append(
                {
                    "pher_key": key,
                    "kind": kind,
                    "tau": tau,
                    "bel_evil": bel,
                    "sensor": d.get("sensor", ""),
                }
            )
        rows.sort(key=lambda n: -n["tau"])
        return rows

    try:
        nodes = await asyncio.wait_for(_scan(), timeout=_VALKEY_TIMEOUT_S)
    except Exception:
        return JSONResponse({"nodes": [], "valkey_available": False})
    return JSONResponse({"nodes": nodes, "valkey_available": True})


@app.get("/api/pheromones")
async def api_pheromones() -> JSONResponse:
    """Runbook-compatible alias for the live pheromone snapshot."""
    return await api_pher_snapshot()


@app.get("/fragment/cacao", response_class=HTMLResponse)
async def fragment_cacao() -> HTMLResponse:
    """Legacy HTMX fragment retained for the old TUI/dashboard."""
    try:
        vc = await asyncio.wait_for(get_valkey(), timeout=_VALKEY_TIMEOUT_S)
    except Exception:
        return HTMLResponse("<table><tbody><tr><td>valkey unavailable</td></tr></tbody></table>")
    out: list[str] = ["<table><thead><tr><th>inst</th><th>status</th><th>cursor</th></tr></thead><tbody>"]
    async for raw in vc.scan_iter(match="cacao:instance:*", count=100):
        key = raw.decode() if isinstance(raw, bytes) else raw
        h = await vc.hgetall(key)
        d = {
            (k.decode() if isinstance(k, bytes) else k): (
                v.decode() if isinstance(v, bytes) else v
            )
            for k, v in h.items()
        }
        out.append(
            f"<tr><td>{key.split(':')[-1][:8]}</td>"
            f"<td>{d.get('status', '-')}</td>"
            f"<td>{d.get('step_cursor', '0')}</td></tr>"
        )
    out.append("</tbody></table>")
    return HTMLResponse("".join(out))


@app.get("/api/cacao/instances")
async def api_cacao_instances() -> JSONResponse:
    async def _scan() -> list[dict]:
        rows: list[dict] = []
        vc = await get_valkey()
        async for raw in vc.scan_iter(match="cacao:instance:*", count=100):
            key = raw.decode() if isinstance(raw, bytes) else raw
            h = await vc.hgetall(key)
            d = {
                (k.decode() if isinstance(k, bytes) else k): (
                    v.decode() if isinstance(v, bytes) else v
                )
                for k, v in h.items()
            }
            rows.append({"instance_id": key.split(":")[-1], **d})
        return rows

    try:
        out = await asyncio.wait_for(_scan(), timeout=_VALKEY_TIMEOUT_S)
    except Exception:
        return JSONResponse({"instances": [], "valkey_available": False})
    return JSONResponse({"instances": out, "valkey_available": True})


@app.get("/api/cacao/recent")
async def api_cacao_recent(n: int = 32) -> JSONResponse:
    """Runbook-compatible recent-instance list."""
    n = max(1, min(int(n), 100))
    payload = await api_cacao_instances()
    data = json.loads(payload.body.decode("utf-8"))
    instances = data.get("instances", []) if isinstance(data, dict) else []
    instances.sort(key=lambda row: int(row.get("started_ns", 0) or 0), reverse=True)
    return JSONResponse(instances[:n])


@app.get("/api/health")
async def api_health() -> dict:
    health = {"dashboard": True, "ledger": False, "valkey": False}
    try:
        r = LedgerReader()
        try:
            await r.tip()
        finally:
            r.close()
        health["ledger"] = True
    except Exception:
        health["ledger"] = False
    try:
        await asyncio.wait_for(get_valkey(), timeout=_VALKEY_TIMEOUT_S)
        health["valkey"] = True
    except Exception:
        health["valkey"] = False
    health["ok"] = all(health.values())
    return health


# ---------------------------------------------------------------------------
# SSE — shadow-channel firehose
# ---------------------------------------------------------------------------


async def _sse_shadow(channel: str) -> AsyncIterator[bytes]:
    """Forward one Valkey pub/sub channel as Server-Sent Events.

    If Valkey is unreachable, emits a deferred-keepalive comment stream and
    retries the connection every 4s. The front-end's EventSource auto-reconnect
    handles the case where the connection is closed by an upstream proxy.
    """
    while True:
        try:
            vc = await get_valkey()
            pubsub = vc.pubsub()
            await pubsub.subscribe(channel)
        except Exception:
            yield b": valkey-unavailable\n\n"
            await asyncio.sleep(4.0)
            continue
        try:
            while True:
                try:
                    msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                except Exception:
                    yield b": valkey-error\n\n"
                    break
                if msg is None:
                    yield b": keepalive\n\n"
                    continue
                data = msg.get("data")
                if isinstance(data, (bytes, bytearray)):
                    yield b"data: " + bytes(data) + b"\n\n"
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception:
                pass
        # If we fall out of the inner loop (error path), back off and retry.
        await asyncio.sleep(2.0)


@app.get("/stream/consensus")
async def stream_consensus(_req: Request) -> StreamingResponse:
    from findevil.mcp_server.shadow import SHADOW_CHAN_CONSENSUS

    return StreamingResponse(
        _sse_shadow(SHADOW_CHAN_CONSENSUS), media_type="text/event-stream"
    )


@app.get("/stream/fractal")
async def stream_fractal(_req: Request) -> StreamingResponse:
    from findevil.mcp_server.shadow import SHADOW_CHAN_FRACTAL

    return StreamingResponse(
        _sse_shadow(SHADOW_CHAN_FRACTAL), media_type="text/event-stream"
    )


@app.get("/stream/pher")
async def stream_pher(_req: Request) -> StreamingResponse:
    from findevil.mcp_server.shadow import SHADOW_CHAN_PHER

    return StreamingResponse(
        _sse_shadow(SHADOW_CHAN_PHER), media_type="text/event-stream"
    )


@app.get("/sse/pheromones")
async def sse_pheromones(_req: Request) -> StreamingResponse:
    return await stream_pher(_req)


@app.get("/stream/mitigation")
async def stream_mitigation(_req: Request) -> StreamingResponse:
    from findevil.mcp_server.shadow import SHADOW_CHAN_MITIGATION

    return StreamingResponse(
        _sse_shadow(SHADOW_CHAN_MITIGATION), media_type="text/event-stream"
    )


# ---------------------------------------------------------------------------
# SSE — ledger tail (sqlite-polling because Writer is sync, no shadow chan)
# ---------------------------------------------------------------------------


async def _sse_ledger_tail(poll_sec: float = 0.5) -> AsyncIterator[bytes]:
    """Tail the forensic ledger by sequence. Emits newly-committed entries."""
    last_seq = 0
    # Bootstrap: send the most recent 8 entries on connect so the HUD is not blank.
    try:
        r = LedgerReader()
        try:
            seed = await r.recent(8)
        finally:
            r.close()
        for row in reversed(seed):
            yield b"data: " + json.dumps(row).encode() + b"\n\n"
            last_seq = max(last_seq, int(row.get("seq", 0)))
    except Exception:
        # No DB yet — send a keepalive and let the poll loop pick up entries
        # whenever the writer materializes them.
        yield b": ledger-bootstrap-deferred\n\n"

    while True:
        await asyncio.sleep(poll_sec)
        try:
            r = LedgerReader()
            try:
                rows = await r.recent(64)
            finally:
                r.close()
        except Exception:
            yield b": ledger-poll-error\n\n"
            continue
        # rows are DESC by seq; take only ones we haven't sent
        new = [row for row in rows if int(row.get("seq", 0)) > last_seq]
        # Emit oldest-first so the HUD scrolls naturally
        for row in reversed(new):
            yield b"data: " + json.dumps(row).encode() + b"\n\n"
            last_seq = max(last_seq, int(row.get("seq", 0)))
        if not new:
            yield b": keepalive\n\n"


@app.get("/stream/ledger")
async def stream_ledger(_req: Request) -> StreamingResponse:
    return StreamingResponse(_sse_ledger_tail(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run() -> None:  # entrypoint: `findevil-dashboard`
    import uvicorn

    from findevil.observability.logging import configure_logging

    configure_logging(service="findevil-dashboard")
    uvicorn.run(
        app,
        host=settings.ui.http_host,
        port=settings.ui.http_port,
        log_level="info",
    )


if __name__ == "__main__":  # pragma: no cover
    run()
