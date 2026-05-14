"""Textual TUI — six-pane layout for FIND EVIL (blueprint Part 15.1).

Layout (from the blueprint):

   ┌──────────────────────────────┬─────────────────┐
   │ consensus feed               │ ledger tip      │
   ├──────────────────────────────┼─────────────────┤
   │ ATT&CK timeline              │ CACAO queue     │
   ├──────────────────────────────┼─────────────────┤
   │ pheromone heat               │ fractal tree    │
   └──────────────────────────────┴─────────────────┘

Subscribes to the Valkey shadow channels for consensus/fractal and polls
the MCP resources for slow-moving pheromone snapshots + ledger tip.
"""

from __future__ import annotations

import asyncio
import json

from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.widgets import Footer, Header

from findevil.ledger.reader import LedgerReader
from findevil.transport.valkey import get_valkey

from .panes import (
    AttackTimelinePane,
    CacaoQueuePane,
    ConsensusFeedPane,
    FractalTreePane,
    LedgerTipPane,
    PheromoneHeatPane,
)


class FindEvilApp(App):
    CSS = """
    Screen { layout: vertical; }
    Grid { grid-size: 2 3; grid-gutter: 1; }
    """
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Force refresh"),
    ]

    def __init__(self):
        super().__init__()
        self.consensus = ConsensusFeedPane(id="p-consensus")
        self.ledger_tip = LedgerTipPane(id="p-ledger")
        self.attack = AttackTimelinePane(id="p-attack")
        self.cacao = CacaoQueuePane(id="p-cacao")
        self.pher = PheromoneHeatPane(id="p-pher")
        self.fractal = FractalTreePane(id="p-fractal")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        grid = Grid(
            self.consensus,
            self.ledger_tip,
            self.attack,
            self.cacao,
            self.pher,
            self.fractal,
        )
        yield grid
        yield Footer()

    async def on_mount(self) -> None:
        self.set_interval(1.0, self._tick_slow)
        asyncio.create_task(self._shadow_reader())

    async def _tick_slow(self) -> None:
        # Pheromone heat & ledger tip & attack path refresh on 1 Hz
        try:
            vc = await get_valkey()
            rows = []
            async for raw in vc.scan_iter(match="pher:*", count=200):
                k = raw.decode() if isinstance(raw, bytes) else raw
                if k.endswith(":sensors") or ":history" in k:
                    continue
                h = await vc.hgetall(k)
                h = {
                    (kk.decode() if isinstance(kk, bytes) else kk): (
                        vv.decode() if isinstance(vv, bytes) else vv
                    )
                    for kk, vv in h.items()
                }
                kind = (
                    "ip" if k.startswith("pher:ip:") else
                    "hash" if k.startswith("pher:hash:") else
                    "domain" if k.startswith("pher:domain:") else
                    "process" if k.startswith("pher:proc:") else "?"
                )
                rows.append({"kind": kind, "key": k, **h})
            rows.sort(key=lambda r: -float(r.get("tau", 0.0)))
            self.pher.refresh_rows(rows)
        except Exception:
            pass

        try:
            r = LedgerReader()
            tip = await r.tip()
            self.ledger_tip.update_tip(tip)
            r.close()
        except Exception:
            pass

        try:
            vc = await get_valkey()
            state = await vc.hgetall("attack:current_path")
            state = {
                (kk.decode() if isinstance(kk, bytes) else kk): (
                    vv.decode() if isinstance(vv, bytes) else vv
                )
                for kk, vv in state.items()
            }
            techs = json.loads(state.get("techniques", "[]")) if state else []
            self.attack.update_chain(techs)
        except Exception:
            pass

    async def _shadow_reader(self) -> None:
        from findevil.mcp_server.shadow import (
            SHADOW_CHAN_CONSENSUS,
            SHADOW_CHAN_FRACTAL,
        )

        vc = await get_valkey()
        pubsub = vc.pubsub()
        await pubsub.subscribe(SHADOW_CHAN_CONSENSUS, SHADOW_CHAN_FRACTAL)
        try:
            while True:
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if msg is None:
                    continue
                chan = msg.get("channel")
                if isinstance(chan, bytes):
                    chan = chan.decode()
                data = msg.get("data")
                if not isinstance(data, (bytes, bytearray)):
                    continue
                if chan == SHADOW_CHAN_CONSENSUS:
                    self.consensus.feed_message(data)
                elif chan == SHADOW_CHAN_FRACTAL:
                    try:
                        env = json.loads(data)
                        payload = env.get("payload")
                        body = json.loads(payload) if isinstance(payload, (str, bytes)) else env
                    except ValueError:
                        continue
                    if "spawn_id" in body and "depth" in body:
                        self.fractal.add_spawn(body)
                    if body.get("finding") is not None or body.get("terminated_by_ttl"):
                        self.fractal.mark_report(body)
        finally:
            try:
                await pubsub.close()
            except Exception:
                pass

    def action_refresh(self) -> None:
        asyncio.create_task(self._tick_slow())


def run() -> None:  # entrypoint: `findevil-tui`
    FindEvilApp().run()


if __name__ == "__main__":  # pragma: no cover
    run()
