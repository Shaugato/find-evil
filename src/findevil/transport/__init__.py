"""Transport plane — NATS JetStream, Valkey UDS, ZeroMQ ipc://.

Attributes are resolved lazily (PEP 562) so that importing a sibling package does
not eagerly drag in the NATS or Valkey clients. Tools + offline unit tests that
never touch the transport plane can import `findevil.tools.shims.*` without
needing `nats`, `valkey`, or `pyzmq` installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = [
    "NatsBus",
    "SharedBufDescriptor",
    "ValkeyClient",
    "ZmqBus",
    "get_nats",
    "get_valkey",
    "valkey_client",
]


if TYPE_CHECKING:  # pragma: no cover - static type checking only
    from .nats_bus import NatsBus, get_nats
    from .valkey import ValkeyClient, get_valkey, valkey_client
    from .zmq_bus import SharedBufDescriptor, ZmqBus


def __getattr__(name: str):
    if name in {"NatsBus", "get_nats"}:
        from .nats_bus import NatsBus, get_nats

        return {"NatsBus": NatsBus, "get_nats": get_nats}[name]
    if name in {"ValkeyClient", "get_valkey", "valkey_client"}:
        from .valkey import ValkeyClient, get_valkey, valkey_client

        return {
            "ValkeyClient": ValkeyClient,
            "get_valkey": get_valkey,
            "valkey_client": valkey_client,
        }[name]
    if name in {"ZmqBus", "SharedBufDescriptor"}:
        from .zmq_bus import SharedBufDescriptor, ZmqBus

        return {"ZmqBus": ZmqBus, "SharedBufDescriptor": SharedBufDescriptor}[name]
    raise AttributeError(f"module 'findevil.transport' has no attribute {name!r}")
