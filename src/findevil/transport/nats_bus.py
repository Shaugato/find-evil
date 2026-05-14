"""NATS JetStream wrapper — durable + file-stored structured path.

Subject catalog (per blueprint Part 3.2):
  find.>                 raw-firehose stream
  ledger.v1.finding.>    ledger-v1 stream (consensus findings + narrator out)
  ledger.late.>          ledger-late stream (late-arriving events per Part 8.2)
  ledger.dupe.>          ledger-dupe stream (suppressed duplicate event ids)
  consensus.v1.finding.> consensus-v1 stream
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

import msgspec
import nats
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg
from nats.js.client import JetStreamContext
from nats.js.errors import BadRequestError, NotFoundError

from findevil.config.settings import settings

MessageHandler = Callable[[Msg], Awaitable[None]]


@dataclass(frozen=True)
class StreamSpec:
    name: str
    subjects: tuple[str, ...]
    max_bytes: int


STREAM_SPECS: tuple[StreamSpec, ...] = (
    StreamSpec(
        name="ledger-v1",
        subjects=("ledger.v1.finding.>",),
        max_bytes=2 * 1024 * 1024 * 1024,
    ),
    StreamSpec(
        name="ledger-late",
        subjects=("ledger.late.>",),
        max_bytes=512 * 1024 * 1024,
    ),
    StreamSpec(
        name="ledger-dupe",
        subjects=("ledger.dupe.>",),
        max_bytes=512 * 1024 * 1024,
    ),
    StreamSpec(
        name="consensus-v1",
        subjects=("consensus.v1.finding.>",),
        max_bytes=1024 * 1024 * 1024,
    ),
    StreamSpec(
        name="raw-firehose",
        subjects=("find.>", "ledger.raw.>"),
        max_bytes=4 * 1024 * 1024 * 1024,
    ),
)


class NatsBus:
    """Single-connection NATS JetStream helper."""

    def __init__(self, url: Optional[str] = None):
        self._url = url or settings.transport.nats_url
        self._nc: Optional[NATS] = None
        self._js: Optional[JetStreamContext] = None

    async def connect(self) -> None:
        if self._nc is not None:
            return
        self._nc = await nats.connect(
            self._url,
            user=settings.transport.nats_user or None,
            password=settings.transport.nats_password or None,
            allow_reconnect=True,
            max_reconnect_attempts=-1,
        )
        self._js = self._nc.jetstream(domain=settings.transport.nats_jsdomain)

    async def publish(self, subject: str, payload: bytes | dict) -> None:
        assert self._js, "call connect() first"
        data = payload if isinstance(payload, (bytes, bytearray)) else msgspec.json.encode(payload)
        last_exc: BaseException | None = None
        for attempt in range(3):
            try:
                await self._js.publish(subject, data, timeout=5.0)
                return
            except (asyncio.TimeoutError, TimeoutError) as exc:
                last_exc = exc
                await asyncio.sleep(0.1 * (attempt + 1))
        if last_exc is not None:
            raise last_exc

    async def subscribe(
        self,
        subject: str,
        *,
        durable: Optional[str] = None,
        queue: Optional[str] = None,
        callback: Optional[MessageHandler] = None,
    ):
        assert self._js, "call connect() first"
        return await self._js.subscribe(
            subject, durable=durable, queue=queue, cb=callback, manual_ack=callback is None
        )

    async def pull_subscribe(self, subject: str, durable: str):
        assert self._js, "call connect() first"
        return await self._js.pull_subscribe(subject, durable=durable)

    async def ensure_streams(self) -> list[dict]:
        """Create or update the implementation-guide JetStream streams.

        The guide requires four durable streams. This method is intentionally
        idempotent so bootstrap/runbook commands can call it repeatedly.
        """
        assert self._js, "call connect() first"
        from nats.js.api import RetentionPolicy, StorageType, StreamConfig

        out: list[dict] = []
        for spec in STREAM_SPECS:
            cfg = StreamConfig(
                name=spec.name,
                subjects=list(spec.subjects),
                storage=StorageType.FILE,
                retention=RetentionPolicy.LIMITS,
                max_bytes=spec.max_bytes,
                num_replicas=1,
                discard="old",
            )
            status = "created"
            try:
                await self._js.stream_info(spec.name)
                await self._js.update_stream(cfg)
                status = "updated"
            except NotFoundError:
                try:
                    await self._js.add_stream(cfg)
                except BadRequestError as exc:
                    status = f"conflict:{exc}"
            except BadRequestError as exc:
                # Older NATS servers can reject updates that don't change
                # anything. Surface the stream but keep setup idempotent.
                status = f"unchanged:{exc}"
            out.append(
                {
                    "name": spec.name,
                    "subjects": list(spec.subjects),
                    "max_bytes": spec.max_bytes,
                    "status": status,
                }
            )
        return out

    async def close(self) -> None:
        if self._nc is not None:
            await self._nc.close()
            self._nc = None
            self._js = None


_shared_by_loop: dict[asyncio.AbstractEventLoop, NatsBus] = {}


async def get_nats() -> NatsBus:
    loop = asyncio.get_running_loop()
    bus = _shared_by_loop.get(loop)
    if bus is None:
        bus = NatsBus()
        await bus.connect()
        _shared_by_loop[loop] = bus
    return bus


# Subject catalog constants
SUBJ_LEDGER_FINDING = "ledger.v1.finding"
SUBJ_LEDGER_LATE = "ledger.late"
SUBJ_LEDGER_DUPE = "ledger.dupe"
SUBJ_CONSENSUS_FINDING = "consensus.v1.finding"
SUBJ_RAW = "find"
SUBJ_RAW_MALFORMED = "ledger.raw.malformed"
