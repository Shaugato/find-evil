"""Bytewax output sinks — ZMQ consensus firehose + fractal spawn PUSH."""

from __future__ import annotations

from typing import Any

import msgspec
from bytewax.outputs import DynamicSink, StatelessSinkPartition

from findevil.observability.logging import get_logger
from findevil.transport.nats_bus import get_nats
from findevil.transport.zmq_bus import (
    SUBJ_CONSENSUS,
    SUBJ_FRACTAL_SPAWN,
    SUBJ_PHER_UPDATE,
    ZmqBus,
)

log = get_logger("findevil.ingest.sinks")


class _ZmqPartition(StatelessSinkPartition[Any]):
    def __init__(self, subject: str):
        self.bus = ZmqBus.default()
        self.sock = self.bus.pub(subject)
        self.subject = subject

    def write_batch(self, items: list[Any]) -> None:
        for it in items:
            if it is None:
                continue
            frame = it if isinstance(it, (bytes, bytearray)) else msgspec.json.encode(it)
            self.sock.send(bytes(frame))

    def close(self) -> None:
        try:
            self.sock.close(linger=0)
        except Exception:
            pass


class _ZmqPushPartition(_ZmqPartition):
    def __init__(self, subject: str):
        self.bus = ZmqBus.default()
        self.sock = self.bus.push(subject)
        self.subject = subject


class ZmqConsensusSink(DynamicSink[Any]):
    """Bytewax DynamicOutput -> ZMQ PUB `consensus.v1`."""

    def build(self, _step_id: str, _worker_index: int, _worker_count: int):
        return _ZmqPartition(SUBJ_CONSENSUS)


class ZmqPherSink(DynamicSink[Any]):
    """Bytewax DynamicOutput -> ZMQ PUB `pher.update`."""

    def build(self, _step_id: str, _worker_index: int, _worker_count: int):
        return _ZmqPartition(SUBJ_PHER_UPDATE)


class FractalSpawnSink(DynamicSink[Any]):
    """Bytewax DynamicOutput -> ZMQ PUSH `fractal.spawn`."""

    def build(self, _step_id: str, _worker_index: int, _worker_count: int):
        return _ZmqPushPartition(SUBJ_FRACTAL_SPAWN)


class _NatsPartition(StatelessSinkPartition[Any]):
    def __init__(self, subject: str):
        import asyncio

        self.subject = subject
        self.loop = asyncio.new_event_loop()
        self.bus = None

    def _ensure(self) -> None:
        if self.bus is not None:
            return

        async def _bind():
            self.bus = await get_nats()

        self.loop.run_until_complete(_bind())

    def write_batch(self, items: list[Any]) -> None:
        self._ensure()
        assert self.bus is not None

        async def _publish_all():
            for it in items:
                if it is None:
                    continue
                try:
                    await self.bus.publish(self.subject, it)
                except Exception as exc:
                    log.warning(
                        "nats_sink_publish_failed",
                        subject=self.subject,
                        error=type(exc).__name__,
                    )

        self.loop.run_until_complete(_publish_all())

    def close(self) -> None:
        try:
            self.loop.close()
        except Exception:
            pass


class NatsJsonSink(DynamicSink[Any]):
    """Bytewax DynamicOutput -> NATS JetStream JSON subject."""

    def __init__(self, subject: str):
        self.subject = subject

    def build(self, _step_id: str, _worker_index: int, _worker_count: int):
        return _NatsPartition(self.subject)
