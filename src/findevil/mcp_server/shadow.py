"""High-rate shadow channel for MCP (blueprint Part 5.5).

MCP's request/response model and keyspace-notification fan-out are too slow for
sub-ms firehose events (per-packet Zeek records, per-syscall EDR deltas).
Instead, high-frequency pub/sub rides a Valkey pub/sub shadow channel. Clients
that need low-latency state fanout (the dashboard, the narrator) subscribe to
these channels and reconcile against MCP resources on demand.

We forward three streams:

  * `findevil.shadow.pher`   : every pheromone deposit (ip/hash/domain/proc)
  * `findevil.shadow.consensus`  : every fused consensus result
  * `findevil.shadow.fractal` : fractal spawn/report events

Each message is a msgspec.json envelope { ts_ns, subject, payload }.

The shadow channel is UNAUTHENTICATED; only local IPC/UDS binding is safe.
"""

from __future__ import annotations

import time

import anyio
import msgspec

from findevil.observability.logging import get_logger
from findevil.observability.metrics import BACKPRESSURE_DROPS, MCP_WRITE_TPS, SHADOW_DROPS
from findevil.transport.valkey import get_valkey
from findevil.transport.zmq_bus import (
    SUBJ_CONSENSUS,
    SUBJ_FRACTAL_REPORT,
    SUBJ_FRACTAL_SPAWN,
    SUBJ_MITIGATION,
    SUBJ_PHER_UPDATE,
    ZmqBus,
)

log = get_logger("findevil.mcp.shadow")


SHADOW_CHAN_PHER = "findevil.shadow.pher"
SHADOW_CHAN_CONSENSUS = "findevil.shadow.consensus"
SHADOW_CHAN_FRACTAL = "findevil.shadow.fractal"
SHADOW_CHAN_MITIGATION = "findevil.shadow.mitigation"


class _Envelope(msgspec.Struct):
    ts_ns: int
    subject: str
    payload: bytes  # already msgspec-encoded; avoids a re-encode hop


def _envelope(subject: str, payload: bytes) -> bytes:
    return msgspec.json.encode(
        _Envelope(ts_ns=time.time_ns(), subject=subject, payload=payload)
    )


async def _forward(bus: ZmqBus, subject: str, shadow_chan: str) -> None:
    """Pump one ZMQ subject into one Valkey pub/sub channel."""
    vc = await get_valkey()
    sock = bus.sub(subject)
    try:
        while True:
            frame = await sock.recv()
            try:
                env = _envelope(subject, frame)
                await vc.publish(shadow_chan, env)
                MCP_WRITE_TPS.labels(resource_prefix=shadow_chan).inc()
            except Exception:
                SHADOW_DROPS.labels(reason="publish_error").inc()
                BACKPRESSURE_DROPS.labels(source=subject).inc()
                log.exception(
                    "shadow_forward_failed", subject=subject, chan=shadow_chan
                )
    finally:
        sock.close(linger=0)


async def run_shadow_publisher() -> None:
    """Run the shadow publisher forever; one task per firehose subject."""
    bus = ZmqBus.default()
    log.info("shadow_publisher.start")
    async with anyio.create_task_group() as tg:
        tg.start_soon(_forward, bus, SUBJ_PHER_UPDATE, SHADOW_CHAN_PHER)
        tg.start_soon(_forward, bus, SUBJ_CONSENSUS, SHADOW_CHAN_CONSENSUS)
        tg.start_soon(_forward, bus, SUBJ_FRACTAL_SPAWN, SHADOW_CHAN_FRACTAL)
        tg.start_soon(_forward, bus, SUBJ_FRACTAL_REPORT, SHADOW_CHAN_FRACTAL)
        tg.start_soon(_forward, bus, SUBJ_MITIGATION, SHADOW_CHAN_MITIGATION)


if __name__ == "__main__":  # pragma: no cover
    anyio.run(run_shadow_publisher)
