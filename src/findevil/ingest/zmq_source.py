"""Bytewax input source for the ZeroMQ raw firehose."""

from __future__ import annotations

from typing import Iterable

import zmq
from bytewax.inputs import FixedPartitionedSource, StatefulSourcePartition

from findevil.transport.zmq_bus import SUBJ_FIREHOSE, ZmqBus


class _ZmqPartition(StatefulSourcePartition[bytes, None]):
    def __init__(self, batch_size: int = 256):
        self.batch_size = batch_size
        self.ctx = zmq.Context.instance()
        self.sock = self.ctx.socket(zmq.SUB)
        self.sock.set_hwm(8192)
        self.sock.setsockopt(zmq.SUBSCRIBE, b"")
        self.sock.connect(ZmqBus.default()._ipc(SUBJ_FIREHOSE))  # noqa: SLF001

    def next_batch(self) -> Iterable[bytes]:
        frames: list[bytes] = []
        for _ in range(self.batch_size):
            try:
                frames.append(self.sock.recv(flags=zmq.NOBLOCK))
            except zmq.Again:
                break
        return frames

    def snapshot(self) -> None:
        return None

    def close(self) -> None:
        self.sock.close(linger=0)


class ZmqFirehoseSource(FixedPartitionedSource[bytes, None]):
    """Single-partition ZMQ SUB source for `find.firehose`."""

    def list_parts(self) -> list[str]:
        return ["0"]

    def build_part(self, _step_id, _part_key: str, _resume_state):
        return _ZmqPartition()
