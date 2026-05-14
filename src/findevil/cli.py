"""Typer-based CLI — `findevil <command>` (Part 17).

Commands:
  status          show process / service health quick-view
  verify          re-verify the forensic ledger chain
  tip             print ledger tip (seq, hash, anchor)
  recent N        print last N ledger entries
  pheromone KEY   inspect a pheromone key
  demo            run the canned T1059.001 scenario and print latency
  mcp|ingest|watcher|narrator|cacao|tui|dashboard|redteam
                  launch individual services (usually systemd does this)

We intentionally keep the CLI thin — every subcommand just delegates to a module
`run()` entrypoint so the plumbing stays one level deep.
"""

from __future__ import annotations

import asyncio
import json
import sys

import typer

from findevil.config.settings import settings

cli = typer.Typer(add_completion=False, help="FIND EVIL — stigmergic DFIR SOC")


@cli.command()
def status() -> None:
    """Check connectivity to transport dependencies."""
    import socket

    import httpx

    rep: dict[str, object] = {"host_id": settings.host_id}

    def probe_tcp(host: str, port: int, timeout: float = 0.5) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    rep["valkey"] = probe_tcp(settings.transport.valkey_host, settings.transport.valkey_port)
    nats_host, nats_port = (
        settings.transport.nats_url.replace("nats://", "").split(":")
        if "://" in settings.transport.nats_url
        else ("127.0.0.1", "4222")
    )
    rep["nats"] = probe_tcp(nats_host, int(nats_port))
    rep["mcp"] = probe_tcp(settings.mcp.host, settings.mcp.port)
    rep["dashboard"] = probe_tcp(settings.ui.http_host, settings.ui.http_port)
    try:
        r = httpx.get(
            f"http://{settings.inference.llamacpp_host}:{settings.inference.llamacpp_port}/v1/models",
            timeout=10.0,
        )
        rep["inference"] = r.status_code == 200
    except Exception:
        rep["inference"] = False
    typer.echo(json.dumps(rep, indent=2))


@cli.command()
def verify() -> None:
    """Re-verify the full forensic ledger chain."""
    from findevil.ledger.verify import verify_chain

    pk = settings.ledger.ed25519_pk_path.read_bytes()
    ok, tainted = verify_chain(settings.ledger.sqlite_path, pk)
    typer.echo(json.dumps({"ok": ok, "tainted_seqs": tainted}, indent=2))
    if not ok:
        sys.exit(2)


@cli.command()
def tip() -> None:
    """Print ledger tip."""
    from findevil.ledger.reader import LedgerReader

    async def _run():
        r = LedgerReader()
        try:
            return await r.tip()
        finally:
            r.close()

    typer.echo(json.dumps(asyncio.run(_run()), indent=2, default=str))


@cli.command("ledger-tip")
def ledger_tip() -> None:
    """Print ledger tip using the implementation-guide command name."""
    tip()


@cli.command()
def recent(n: int = typer.Argument(20)) -> None:
    """Print last N ledger entries."""
    from findevil.ledger.reader import LedgerReader

    async def _run():
        r = LedgerReader()
        try:
            return await r.recent(n)
        finally:
            r.close()

    typer.echo(json.dumps(asyncio.run(_run()), indent=2, default=str))


@cli.command()
def pheromone(key: str) -> None:
    """Inspect a single pheromone key."""
    from findevil.transport.valkey import get_valkey

    async def _run():
        vc = await get_valkey()
        h = await vc.hgetall(key)
        return {
            (k.decode() if isinstance(k, bytes) else k): (
                v.decode() if isinstance(v, bytes) else v
            )
            for k, v in h.items()
        }

    typer.echo(json.dumps(asyncio.run(_run()), indent=2))


@cli.command("nats-setup")
def nats_setup() -> None:
    """Create/update the guide-mandated NATS JetStream streams."""
    from findevil.transport.nats_bus import NatsBus

    async def _run():
        bus = NatsBus()
        await bus.connect()
        try:
            return await bus.ensure_streams()
        finally:
            await bus.close()

    typer.echo(json.dumps(asyncio.run(_run()), indent=2))


@cli.command()
def demo(scenario: str = "atomic-t1059-001-encoded-ps") -> None:
    """Run one red-team scenario end-to-end."""
    from findevil.redteam.runner import RedTeamRunner
    from findevil.redteam.scenarios import default_scenarios

    target = next((s for s in default_scenarios() if s.id == scenario), None)
    if target is None:
        typer.echo(f"unknown scenario: {scenario}", err=True)
        sys.exit(1)
    runner = RedTeamRunner()
    result = asyncio.run(runner.run_one(target))
    typer.echo(json.dumps(result, indent=2, default=str))


@cli.command("list-tools")
def list_tools() -> None:
    """Enumerate registered MCP tool actuators."""
    from findevil.tools.registry import registered

    for name in registered():
        typer.echo(name)


# ---- service launchers (systemd invokes these) -----------------------------


@cli.command()
def mcp() -> None:
    """Launch the MCP blackboard server."""
    from findevil.mcp_server.server import run as _run

    _run()


@cli.command()
def ingest() -> None:
    """Launch the Bytewax ingest flow."""
    from findevil.ingest.flow import run as _run

    _run()


@cli.command()
def watcher() -> None:
    """Launch the fractal Watcher."""
    from findevil.fractal.watcher import run as _run

    _run()


@cli.command()
def narrator() -> None:
    """Launch the LangGraph narrator."""
    from findevil.narrator.service import run as _run

    _run()


@cli.command()
def cacao() -> None:
    """Launch the CACAO 2.0 executor daemon."""
    from findevil.cacao.executor import run as _run

    _run()


@cli.command()
def tui() -> None:
    """Launch the Textual TUI."""
    from findevil.ui.tui import run as _run

    _run()


@cli.command("demo-tui")
def demo_tui() -> None:
    """Launch the projector Textual TUI using the implementation-guide command name."""
    tui()


@cli.command()
def dashboard() -> None:
    """Launch the FastAPI/HTMX dashboard."""
    from findevil.ui.http import run as _run

    _run()


@cli.command()
def redteam() -> None:
    """Run the default red-team scenarios."""
    from findevil.redteam.runner import run as _run

    _run()


@cli.command()
def anchor_batch(
    batch_size: int = 256,
    offline: bool = typer.Option(
        False,
        "--offline/--online",
        help="Record the anchor locally without submitting to Rekor.",
    ),
) -> None:
    """Anchor the next batch of ledger entries to Rekor (Merkle root)."""
    from findevil.ledger.anchor import anchor_batch as _anchor

    out = asyncio.run(
        _anchor(
            settings.ledger.sqlite_path,
            batch_size=batch_size,
            rekor_submit=not offline,
        )
    )
    typer.echo(json.dumps(out, indent=2, default=str))


def main() -> None:
    cli()


if __name__ == "__main__":  # pragma: no cover
    main()
