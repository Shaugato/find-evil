"""fastmcp 2.x server — the MCP blackboard for Stigmergy (blueprint Part 5).

This process is the SOLE public surface of the blackboard. Swarm agents, the
Narrator, the Watcher/fractal spawner, the dashboard, and external triage clients
all go through MCP — never directly through Valkey/SQLite.

Exposed resources (Table 4):
  - bb://ioc/ip/{addr}
  - bb://ioc/hash/{sha256}
  - bb://ioc/domain/{name}
  - bb://host/{id}/processes
  - bb://attack/current_path
  - bb://control/focus
  - bb://cacao/instance/{uuid}
  - bb://ledger/tip
  - bb://ledger/recent/{n}

Exposed tools (narrow, idempotent):
  - ledger.verify(seq_from, seq_to)
  - ledger.recent(n)
  - swarm.pheromone_snapshot(kind, pattern)
  - control.set_focus(kind, value)
  - every registered findevil.tools.shims actuator, exposed under its registry
    name (e.g. edr.kill_process, volatility.malfind, yara.scan)

The companion `shadow.py` carries high-frequency push events that would overwhelm
MCP's request/response model.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from findevil.config.settings import settings
from findevil.ledger.reader import LedgerReader
from findevil.ledger.verify import verify_chain
from findevil.observability.logging import get_logger
from findevil.transport.valkey import (
    get_valkey,
    pher_domain_key,
    pher_hash_key,
    pher_ip_key,
)

from .resources import (
    AttackPathResource,
    CacaoInstanceResource,
    ControlFocusResource,
    DomainPheromone,
    HashPheromone,
    HostProcessesResource,
    IPPheromone,
    LedgerTip,
)

log = get_logger("findevil.mcp")

_BUILTIN_TOOL_NAMES = {
    "ledger.verify",
    "ledger.recent",
    "swarm.pheromone_snapshot",
    "control.set_focus",
}


class ToolCommand(BaseModel):
    """Strict envelope accepted by dynamic MCP actuator tools."""

    model_config = ConfigDict(extra="allow")
    type: str = Field(default="manual", max_length=64)
    command: str | None = Field(default=None, max_length=256)
    target: dict[str, Any] = Field(default_factory=dict)


def _decode_hash(h: dict[bytes, bytes]) -> dict[str, str]:
    return {
        (k.decode() if isinstance(k, bytes) else k): (
            v.decode() if isinstance(v, bytes) else v
        )
        for k, v in h.items()
    }


def build_server() -> FastMCP:
    mcp = FastMCP(name="findevil.blackboard")

    # ------- pheromone resources ------------------------------------------
    @mcp.resource("bb://ioc/ip/{addr}")
    async def ioc_ip(addr: str) -> IPPheromone:
        vc = await get_valkey()
        state = _decode_hash(await vc.hgetall(pher_ip_key(addr)))
        return IPPheromone(
            addr=addr,
            tau=float(state.get("tau", 0.0)),
            bel_evil=float(state.get("bel_evil", 0.0)),
            pl_evil=float(state.get("pl_evil", 1.0)),
            conflict_K=float(state.get("conflict_K", 0.0)),
            sensor_diversity=int(state.get("sensor_diversity", 0)),
            last_update_ns=int(state.get("last_update_ns", 0)),
            version=int(state.get("version", 0)),
        )

    @mcp.resource("bb://ioc/hash/{sha256}")
    async def ioc_hash(sha256: str) -> HashPheromone:
        vc = await get_valkey()
        state = _decode_hash(await vc.hgetall(pher_hash_key(sha256)))
        return HashPheromone(
            sha256=sha256,
            tau=float(state.get("tau", 0.0)),
            bel_evil=float(state.get("bel_evil", 0.0)),
            pl_evil=float(state.get("pl_evil", 1.0)),
            conflict_K=float(state.get("conflict_K", 0.0)),
            sensor_diversity=int(state.get("sensor_diversity", 0)),
            last_update_ns=int(state.get("last_update_ns", 0)),
            version=int(state.get("version", 0)),
        )

    @mcp.resource("bb://ioc/domain/{name}")
    async def ioc_domain(name: str) -> DomainPheromone:
        vc = await get_valkey()
        state = _decode_hash(await vc.hgetall(pher_domain_key(name)))
        return DomainPheromone(
            domain=name,
            tau=float(state.get("tau", 0.0)),
            bel_evil=float(state.get("bel_evil", 0.0)),
            pl_evil=float(state.get("pl_evil", 1.0)),
            conflict_K=float(state.get("conflict_K", 0.0)),
            sensor_diversity=int(state.get("sensor_diversity", 0)),
            last_update_ns=int(state.get("last_update_ns", 0)),
            version=int(state.get("version", 0)),
        )

    @mcp.resource("bb://host/{id}/processes")
    async def host_processes(id: str) -> HostProcessesResource:
        vc = await get_valkey()
        state = _decode_hash(await vc.hgetall(f"host:{id}:processes"))
        pids = [int(p) for p in json.loads(state.get("pids", "[]"))]
        flagged = json.loads(state.get("flagged", "[]"))
        return HostProcessesResource(
            host_id=id,
            pids=pids,
            flagged=flagged,
            last_update_ns=int(state.get("last_update_ns", 0)),
        )

    @mcp.resource("bb://attack/current_path")
    async def attack_path() -> AttackPathResource:
        vc = await get_valkey()
        state = _decode_hash(await vc.hgetall("attack:current_path"))
        techniques = json.loads(state.get("techniques", "[]"))
        return AttackPathResource(
            techniques=techniques,
            first_seen_ns=int(state.get("first_seen_ns", 0)),
            last_update_ns=int(state.get("last_update_ns", 0)),
        )

    @mcp.resource("bb://control/focus")
    async def control_focus() -> ControlFocusResource:
        vc = await get_valkey()
        state = _decode_hash(await vc.hgetall("control:focus"))
        if not state:
            return ControlFocusResource()
        return ControlFocusResource(
            kind=state.get("kind") or None,  # type: ignore[arg-type]
            value=state.get("value") or None,
            set_by=state.get("set_by") or None,
            set_ns=int(state.get("set_ns", 0)),
        )

    @mcp.resource("bb://cacao/instance/{uuid}")
    async def cacao_instance(uuid: str) -> CacaoInstanceResource:
        vc = await get_valkey()
        state = _decode_hash(await vc.hgetall(f"cacao:instance:{uuid}"))
        if not state:
            return CacaoInstanceResource(
                instance_id=uuid, playbook_id="", status="pending"
            )
        return CacaoInstanceResource(
            instance_id=uuid,
            playbook_id=state.get("playbook_id", ""),
            status=state.get("status", "pending"),  # type: ignore[arg-type]
            started_ns=int(state.get("started_ns", 0)),
            finished_ns=int(state.get("finished_ns", 0)),
            step_cursor=int(state.get("step_cursor", 0)),
            errors=json.loads(state.get("errors", "[]")),
        )

    @mcp.resource("bb://cti/diamond")
    async def cti_diamond() -> dict[str, Any]:
        """Diamond Model relationship graph (FOR578) — last published build."""
        from findevil.cti.diamond import DIAMOND_KEY

        vc = await get_valkey()
        c = await vc._connect()  # noqa: SLF001 - plain GET on a JSON document
        raw = await c.get(DIAMOND_KEY)
        if not raw:
            return {"model": "diamond", "nodes": [], "edges": [], "counts": {}}
        return json.loads(raw)

    @mcp.resource("bb://ledger/tip")
    async def ledger_tip() -> LedgerTip:
        reader = LedgerReader()
        try:
            tip = await reader.tip()
            return LedgerTip(**tip)
        finally:
            reader.close()

    @mcp.resource("bb://ledger/recent/{n}")
    async def ledger_recent(n: str) -> list[dict[str, Any]]:
        try:
            count = max(1, min(500, int(n)))
        except ValueError:
            count = 50
        reader = LedgerReader()
        try:
            return await reader.recent(count)
        finally:
            reader.close()

    # ------- narrow tools --------------------------------------------------
    @mcp.tool(name="ledger.verify")
    async def tool_ledger_verify(seq_from: int = 1, seq_to: int | None = None) -> dict:
        """Re-hash and re-verify the ledger range [seq_from, seq_to]."""
        pk = settings.ledger.ed25519_pk_path.read_bytes()
        ok, tainted = verify_chain(settings.ledger.sqlite_path, pk)
        return {
            "ok": ok,
            "tainted_seqs": tainted,
            "range": [seq_from, seq_to],
        }

    @mcp.tool(name="ledger.recent")
    async def tool_ledger_recent(n: int = 50) -> list[dict]:
        reader = LedgerReader()
        try:
            return await reader.recent(n)
        finally:
            reader.close()

    @mcp.tool(name="swarm.pheromone_snapshot")
    async def tool_pher_snapshot(kind: str, pattern: str = "*") -> list[dict]:
        """Enumerate non-reinforcing pheromone keys matching `pher:{kind}:{pattern}`.

        kind ∈ {ip, hash, domain, proc}.
        """
        if kind not in ("ip", "hash", "domain", "proc"):
            return []
        vc = await get_valkey()
        out: list[dict] = []
        async for raw in vc.scan_iter(match=f"pher:{kind}:{pattern}", count=500):
            k = raw.decode() if isinstance(raw, bytes) else raw
            if k.endswith(":sensors") or ":history" in k:
                continue
            state = _decode_hash(await vc.hgetall(k))
            out.append({"key": k, **state})
            if len(out) >= 1024:
                break
        return out

    @mcp.tool(name="control.set_focus")
    async def tool_set_focus(
        kind: str, value: str, set_by: str = "analyst"
    ) -> ControlFocusResource:
        if kind not in ("ip", "hash", "domain", "process", "host"):
            raise ValueError(f"invalid focus kind: {kind}")
        import time

        vc = await get_valkey()
        now_ns = time.time_ns()
        c = await vc._connect()  # noqa: SLF001 - internal pipeline access
        async with c.pipeline(transaction=True) as pipe:
            await pipe.hset(
                "control:focus",
                mapping={
                    "kind": kind,
                    "value": value,
                    "set_by": set_by,
                    "set_ns": str(now_ns),
                },
            )
            await pipe.execute()
        return ControlFocusResource(kind=kind, value=value, set_by=set_by, set_ns=now_ns)  # type: ignore[arg-type]

    _register_actuator_tools(mcp)

    return mcp


def _register_actuator_tools(mcp: FastMCP) -> None:
    """Expose every registered SIFT/response shim as a fastmcp tool."""
    from findevil.tools.registry import bootstrap, registered, resolve

    bootstrap()

    def _make_tool(tool_name: str):
        async def _tool(commands: list[ToolCommand] | None = None) -> dict[str, Any]:
            fn = resolve(tool_name)
            if fn is None:
                raise ValueError(f"unknown actuator: {tool_name}")
            command_payload = [
                c.model_dump(mode="json") if isinstance(c, ToolCommand) else c
                for c in (commands or [])
            ]
            return await fn(command_payload)

        _tool.__name__ = "tool_" + tool_name.replace(".", "_").replace("-", "_")
        _tool.__doc__ = f"Invoke registered Stigmergy actuator `{tool_name}`."
        return _tool

    for name in registered():
        if name in _BUILTIN_TOOL_NAMES:
            continue
        mcp.tool(name=name)(_make_tool(name))


async def _keyspace_notifier(mcp: FastMCP) -> None:
    """Subscribe to Valkey keyspace notifications and fire resource-updated events.

    Requires `notify-keyspace-events KEA` in valkey.conf. Every change on a
    `pher:*`, `host:*`, `control:*`, `attack:*`, or `cacao:*` key is translated
    to the matching bb:// URI and emitted to all MCP subscribers.
    """
    vc = await get_valkey()
    pubsub = vc.pubsub()
    # db 0 default channel prefix
    await pubsub.psubscribe("__keyspace@0__:*")
    log.info("mcp.keyspace_notifier.start")
    try:
        async for msg in pubsub.listen():  # type: ignore[union-attr]
            if not msg or msg.get("type") not in ("pmessage", "message"):
                continue
            chan = msg["channel"]
            if isinstance(chan, bytes):
                chan = chan.decode()
            # chan is "__keyspace@0__:<key>"
            key = chan.split(":", 1)[1] if ":" in chan else chan
            uri = _key_to_uri(key)
            if uri is None:
                continue
            try:
                # fastmcp 2.x exposes notify_resource_updated on the server instance
                notify = getattr(mcp, "notify_resource_updated", None)
                if notify is not None:
                    await notify(uri)
            except Exception:  # pragma: no cover - never kill the notifier
                log.exception("notify_resource_updated failed", uri=uri)
    except asyncio.CancelledError:
        pass
    finally:
        try:
            await pubsub.close()
        except Exception:
            pass


def _key_to_uri(key: str) -> str | None:
    """Translate internal Valkey keys to bb:// URIs."""
    if key.startswith("pher:ip:"):
        return f"bb://ioc/ip/{key[len('pher:ip:'):]}"
    if key.startswith("pher:hash:"):
        return f"bb://ioc/hash/{key[len('pher:hash:'):]}"
    if key.startswith("pher:domain:"):
        return f"bb://ioc/domain/{key[len('pher:domain:'):]}"
    if key.startswith("host:") and key.endswith(":processes"):
        host_id = key[len("host:") : -len(":processes")]
        return f"bb://host/{host_id}/processes"
    if key == "attack:current_path":
        return "bb://attack/current_path"
    if key == "control:focus":
        return "bb://control/focus"
    if key.startswith("cacao:instance:"):
        return f"bb://cacao/instance/{key[len('cacao:instance:'):]}"
    return None


async def _anchor_age_refresher(interval_s: float = 60.0) -> None:
    """Keep findevil_rekor_anchor_age_seconds growing between anchor runs.

    Anchoring itself is a oneshot CLI job, so the gauge must be owned by a
    long-running process — this server is the natural home (it already owns
    the ledger tools and the :+1 metrics port).
    """
    from findevil.ledger.anchor import update_anchor_age

    try:
        while True:
            try:
                await asyncio.to_thread(update_anchor_age, settings.ledger.sqlite_path)
            except Exception:  # pragma: no cover - never kill the refresher
                log.exception("anchor_age_refresh failed")
            await asyncio.sleep(interval_s)
    except asyncio.CancelledError:
        pass


async def _run_async() -> None:
    from .shadow import run_shadow_publisher

    mcp = build_server()
    # background tasks: keyspace notifier + shadow publisher + anchor-age gauge
    notifier_task = asyncio.create_task(_keyspace_notifier(mcp))
    shadow_task = asyncio.create_task(run_shadow_publisher())
    anchor_age_task = asyncio.create_task(_anchor_age_refresher())
    try:
        # fastmcp exposes an async `.run_http_async(...)` helper; fall back to
        # its blocking .run in a thread if the async API is not available.
        runner = getattr(mcp, "run_http_async", None)
        if runner is not None:
            await runner(
                host=settings.mcp.host,
                port=settings.mcp.port,
                path=settings.mcp.path,
            )
        else:
            await asyncio.to_thread(
                mcp.run,
                transport="http",
                host=settings.mcp.host,
                port=settings.mcp.port,
                path=settings.mcp.path,
            )
    finally:
        notifier_task.cancel()
        shadow_task.cancel()
        anchor_age_task.cancel()
        for t in (notifier_task, shadow_task, anchor_age_task):
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass


def run() -> None:  # entry-point: `findevil mcp`
    os.umask(0o077)
    from findevil.observability.logging import configure_logging
    from findevil.observability.metrics import start_metrics_server
    from findevil.observability.tracing import init_tracing

    configure_logging(service="findevil-mcp")
    init_tracing(service_name="findevil-mcp")
    start_metrics_server(settings.observability.prometheus_port + 1)
    asyncio.run(_run_async())


def run_stdio() -> None:
    """Serve the SAME typed-tool catalog over **stdio** for standard MCP clients
    (Claude Desktop / Claude Code / Cursor / Cline) to spawn directly.

    Reuses ``build_server()`` — one tool catalog, one guardrail (no execute_shell).
    The HTTP service's background tasks (keyspace notifier, shadow publisher,
    anchor-age gauge) are intentionally NOT started here: they are live-service
    concerns and would require NATS just to connect, whereas tool discovery and
    invocation do not need them. Resources still read Valkey lazily when present.

    CRITICAL: the stdio transport owns **stdout** for JSON-RPC, so we must not let
    the project's stdout JSON logger (configure_logging) run — it would corrupt the
    protocol. stdlib logging is pinned to stderr and any build-time stdout is
    redirected to stderr; FastMCP itself logs to stderr.
    """
    import contextlib
    import logging
    import sys

    os.umask(0o077)
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING, force=True)
    with contextlib.redirect_stdout(sys.stderr):
        mcp = build_server()
    mcp.run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover
    run_stdio()
