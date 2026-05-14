"""Watcher daemon — spawns ephemeral pivot agents under a strict budget.

Blueprint Part 9.2:
  * consumes `fractal.spawn` ZMQ PULL
  * enforces max_depth, max_width, and a GPU-slot semaphore
  * spawns `run_pivot` asyncio tasks, each with its own TTL
  * forwards PivotReport onto `fractal.report` ZMQ PUSH
  * also routes reports that produce new `follow_ups` back into fractal.spawn
    up to `max_depth`
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any

import msgspec

from findevil.config.settings import settings
from findevil.inference.facade import InferenceFacade
from findevil.observability.logging import get_logger
from findevil.observability.metrics import FRACTAL_SPAWNS
from findevil.transport.zmq_bus import (
    SUBJ_FRACTAL_REPORT,
    SUBJ_FRACTAL_SPAWN,
    ZmqBus,
)

from .agent import PivotReport, PivotSpawn, run_pivot

log = get_logger("findevil.fractal.watcher")


class DepthExceeded(Exception):
    """Raised when a pivot spawn exceeds the configured recursion depth."""


class WidthExceeded(Exception):
    """Raised when concurrent pivot spawns exceed the configured width."""


class Watcher:
    def __init__(
        self,
        _infer: Any | None = None,
        _writer: Any | None = None,
        *,
        max_concurrency: int = 4,
        facade: InferenceFacade | None = None,
    ):
        self.bus = ZmqBus.default()
        self.sem = asyncio.Semaphore(max_concurrency)
        self.facade = facade or InferenceFacade()
        self._running = False
        self._tasks: set[asyncio.Task] = set()
        self.live = 0

    def _track(self, task: asyncio.Task) -> None:
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _dispatch(
        self, spawn: PivotSpawn, report_sock
    ) -> PivotReport:
        if spawn.depth >= settings.fractal.max_depth:
            raise DepthExceeded()
        if self.live >= settings.fractal.max_width:
            raise WidthExceeded()
        self.live += 1
        try:
            async with self.sem:
                FRACTAL_SPAWNS.labels(seed_technique=spawn.seed_technique or "unknown").inc()
                rep = await run_pivot(spawn, facade=self.facade)
        finally:
            self.live -= 1

        # emit report
        try:
            await report_sock.send(msgspec.json.encode(rep))
        except Exception:
            log.exception("report_send_failed", spawn_id=spawn.spawn_id)

        # cascading follow-ups (H3 recursion) — depth-limited
        if (
            rep.ok
            and rep.finding
            and rep.depth + 1 < settings.fractal.max_depth
            and rep.finding.get("follow_ups")
        ):
            follow_ups = rep.finding["follow_ups"][: settings.fractal.max_width]
            for fu in follow_ups:
                child = PivotSpawn(
                    spawn_id=uuid.uuid4().hex,
                    seed_technique=spawn.seed_technique,
                    scoped_prompt=fu.get("scoped_prompt", spawn.scoped_prompt),
                    exhibits=fu.get("exhibits", spawn.exhibits),
                    ttl_ms=min(spawn.ttl_ms, settings.fractal.ttl_ms),
                    depth=rep.depth + 1,
                    parent_id=spawn.spawn_id,
                )
                self._track(asyncio.create_task(self._dispatch(child, report_sock)))
        return rep

    async def run_forever(self) -> None:
        # PULL end of `fractal.spawn` (Watcher consumes from Bytewax + narrator)
        spawn_pull = self.bus.pull(SUBJ_FRACTAL_SPAWN)
        # PUSH end of `fractal.report`
        report_push = self.bus.push(SUBJ_FRACTAL_REPORT)
        self._running = True
        log.info("watcher.start")

        try:
            while self._running:
                raw = await spawn_pull.recv()
                try:
                    spawn = msgspec.json.decode(raw, type=PivotSpawn)
                except Exception:
                    log.exception("spawn_decode_failed")
                    continue
                # hard cap: never spawn past max_depth
                if spawn.depth >= settings.fractal.max_depth:
                    continue
                t = asyncio.create_task(self._dispatch(spawn, report_push))
                self._track(t)
        finally:
            for t in self._tasks:
                t.cancel()
            try:
                spawn_pull.close(linger=0)
                report_push.close(linger=0)
            except Exception:
                pass
            try:
                await self.facade.close()
            except Exception:
                pass

    def stop(self) -> None:
        self._running = False


def run() -> None:  # entrypoint: `findevil-watcher`
    os.umask(0o077)
    from findevil.observability.logging import configure_logging
    from findevil.observability.metrics import start_metrics_server
    from findevil.observability.tracing import init_tracing

    configure_logging(service="findevil-watcher")
    init_tracing(service_name="findevil-watcher")
    start_metrics_server(settings.observability.prometheus_port + 3)

    async def _main():
        w = Watcher(
            max_concurrency=int(
                os.environ.get("FINDEVIL_WATCHER_CONC", str(settings.fractal.max_width))
            )
        )
        try:
            await w.run_forever()
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass

    asyncio.run(_main())


if __name__ == "__main__":  # pragma: no cover
    run()
