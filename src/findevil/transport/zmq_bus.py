"""ZeroMQ hot-path transport (blueprint Part 3.3).

Subjects (NATS-style namespaces projected onto ZMQ ipc socket files):
  find.*            - raw firehose events (PUB/SUB)
  pher.update.*     - threshold evaluator deposits (PUSH/PULL)
  consensus.v1.*    - fused findings (PUB/SUB)
  fractal.spawn     - Watcher -> ephemeral agents (REQ/REP)
  fractal.report    - ephemeral -> Watcher (PUSH/PULL)
  mitigation.fire   - CACAO trigger (PUB/SUB)

Zero-copy descriptor convention: payloads > 64 KiB should be placed in an anonymous
shared-mem segment and published as a SharedBufDescriptor. Consumers resolve via
multiprocessing.shared_memory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import msgspec
import zmq
import zmq.asyncio

from findevil.config.settings import settings


class SharedBufDescriptor(msgspec.Struct, frozen=True):
    """Zero-copy payload descriptor used when events exceed a small inlined size."""

    shm_name: str
    offset: int
    size: int
    sha256: bytes


class ZmqBus:
    """Thin wrapper around a shared asyncio ZMQ context.

    One bus per process. Socket names map 1:1 to files under ipc_dir so systemd-tmpfiles
    can pre-create the directory with group-writable perms.
    """

    _instance: Optional["ZmqBus"] = None

    def __init__(self, run_dir: Optional[Path] = None):
        self.ctx = zmq.asyncio.Context.instance()
        self.run_dir = Path(run_dir or settings.transport.zmq_ipc_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def default(cls) -> "ZmqBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ipc(self, subject: str) -> str:
        # Blueprint says ipc:// under /opt/findevil/run/zmq — mirror on non-Linux as ipc://tmp.
        safe = subject.replace("/", "_")
        return f"ipc://{(self.run_dir / safe).as_posix()}.sock"

    # ----- helpers -----------------------------------------------------------
    def pub(self, subject: str) -> zmq.asyncio.Socket:
        s = self.ctx.socket(zmq.PUB)
        s.set_hwm(8192)
        s.bind(self._ipc(subject))
        return s

    def sub(self, subject: str) -> zmq.asyncio.Socket:
        s = self.ctx.socket(zmq.SUB)
        s.set_hwm(8192)
        s.connect(self._ipc(subject))
        s.setsockopt(zmq.SUBSCRIBE, b"")
        return s

    def push(self, subject: str) -> zmq.asyncio.Socket:
        s = self.ctx.socket(zmq.PUSH)
        s.set_hwm(8192)
        s.bind(self._ipc(subject))
        return s

    def pull(self, subject: str) -> zmq.asyncio.Socket:
        s = self.ctx.socket(zmq.PULL)
        s.set_hwm(8192)
        s.connect(self._ipc(subject))
        return s

    def rep(self, subject: str) -> zmq.asyncio.Socket:
        s = self.ctx.socket(zmq.REP)
        s.bind(self._ipc(subject))
        return s

    def req(self, subject: str) -> zmq.asyncio.Socket:
        s = self.ctx.socket(zmq.REQ)
        s.connect(self._ipc(subject))
        return s

    def close(self) -> None:
        self.ctx.destroy(linger=0)


# ----- canonical subject strings (single source of truth) -------------------

SUBJ_FIREHOSE = "find.firehose"
SUBJ_PHER_UPDATE = "pher.update"
SUBJ_CONSENSUS = "consensus.v1"
SUBJ_FRACTAL_SPAWN = "fractal.spawn"
SUBJ_FRACTAL_REPORT = "fractal.report"
SUBJ_MITIGATION = "mitigation.fire"
