"""Bytewax custom input source backed by NATS JetStream pull subscription.

We use pull_subscribe so back-pressure propagates; if the downstream windowing
stalls we simply stop pulling. Each partition is one NATS consumer name (durable)
so horizontal scale-out is a matter of `--workers`.
"""

from __future__ import annotations

import asyncio
from typing import Iterable

from bytewax.inputs import FixedPartitionedSource, StatefulSourcePartition

from findevil.transport.nats_bus import get_nats


class _NatsPartition(StatefulSourcePartition[bytes, None]):
    """Bytewax StatefulSourcePartition wrapping a durable pull subscription."""

    def __init__(self, subject: str, durable: str, batch_size: int = 256):
        self.subject = subject
        self.durable = durable
        self.batch_size = batch_size
        self._sub = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def _ensure(self):
        if self._sub is not None:
            return
        if self._loop is None:
            self._loop = asyncio.new_event_loop()

        async def _bind():
            bus = await get_nats()
            self._sub = await bus.pull_subscribe(self.subject, durable=self.durable)

        self._loop.run_until_complete(_bind())

    async def _downstream_ready(self) -> bool:
        """Return False when Valkey is unavailable so JetStream keeps messages."""
        try:
            from findevil.transport.valkey import get_valkey

            vc = await get_valkey()
            c = await vc._connect()  # noqa: SLF001
            await c.ping()
            return True
        except Exception:
            return False

    def next_batch(self) -> Iterable[bytes]:
        self._ensure()
        assert self._sub is not None and self._loop is not None

        async def _pull():
            if not await self._downstream_ready():
                return []
            try:
                msgs = await self._sub.fetch(self.batch_size, timeout=0.5)
            except Exception:
                return []
            frames = []
            for m in msgs:
                frames.append(m.data)
                try:
                    await m.ack()
                except Exception:
                    pass
            return frames

        return list(self._loop.run_until_complete(_pull()))

    def snapshot(self) -> None:
        # Positions are tracked server-side by the durable name — no local state.
        return None

    def close(self) -> None:
        if self._loop is not None:
            self._loop.close()
            self._loop = None


class NatsRawSource(FixedPartitionedSource[bytes, None]):
    """Bytewax dynamic input source. Lazy-binds so import doesn't require NATS up."""

    def __init__(self, subject: str = "find.>", durable_prefix: str = "findevil-ingest"):
        self.subject = subject
        self.durable_prefix = durable_prefix

    def list_parts(self) -> list[str]:
        # Single partition is sufficient for the lab-scale target (<= 10k evt/s).
        # Scaling to multi-partition would require subject-space sharding upstream.
        return ["0"]

    def build_part(self, _step_id, part_key: str, _resume_state):
        return _NatsPartition(
            subject=self.subject, durable=f"{self.durable_prefix}-{part_key}"
        )
