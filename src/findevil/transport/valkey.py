"""Valkey (Redis-compatible) async client — unix-socket primary.

Per blueprint Part 3.1 we disable TCP entirely (`port 0`) and connect over UDS. A
global `valkey_client` singleton is exported so the MCP server, swarm decay worker,
Bytewax dataflow, and Watcher all share a single connection pool.

A Lua CAS script and a decay script are preloaded on first use.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import redis.asyncio as redis

from findevil.config.settings import settings

LUA_CAS = """
-- optimistic-version CAS for pheromone keys (blueprint 5.7)
local key = KEYS[1]
local expected_ver = tonumber(ARGV[1])
local cur = tonumber(redis.call('HGET', key, 'version') or '0')
if cur ~= expected_ver then return {0, cur} end
for i = 2, #ARGV, 2 do
  redis.call('HSET', key, ARGV[i], ARGV[i+1])
end
local new_ver = expected_ver + 1
redis.call('HSET', key, 'version', new_ver)
return {1, new_ver}
"""

LUA_DECAY = """
-- Dorigo-style tau decay with MAX-MIN clamps (blueprint 7.1.1)
local tau = tonumber(redis.call('HGET', KEYS[1], 'tau') or '0')
local rho = tonumber(ARGV[1])
local hi  = tonumber(ARGV[2])
local lo  = tonumber(ARGV[3])
local nw = math.max(lo, math.min(hi, (1 - rho) * tau))
redis.call('HSET', KEYS[1], 'tau', string.format('%.6f', nw))
return tostring(nw)
"""

LUA_DEPOSIT = """
-- Atomic pheromone deposit + bel/pl update with sensor diversity tracking
local key = KEYS[1]
local tau_delta = tonumber(ARGV[1])
local bel = tonumber(ARGV[2])
local pl  = tonumber(ARGV[3])
local K   = tonumber(ARGV[4])
local sensor = ARGV[5]
local tau_max = tonumber(ARGV[6])
local cur_tau = tonumber(redis.call('HGET', key, 'tau') or '0')
local new_tau = math.min(tau_max, cur_tau + tau_delta)
redis.call('HSET', key, 'tau', string.format('%.6f', new_tau),
                      'bel_evil', string.format('%.6f', bel),
                      'pl_evil', string.format('%.6f', pl),
                      'conflict_K', string.format('%.6f', K),
                      'last_update_ns', ARGV[7])
redis.call('SADD', key .. ':sensors', sensor)
redis.call('HSET', key, 'sensor_diversity', redis.call('SCARD', key .. ':sensors'))
return new_tau
"""


class ValkeyClient:
    """Lazy-wrapped async Valkey client with preloaded Lua scripts."""

    def __init__(
        self,
        *,
        unix_socket_path: Optional[Path] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        self._path = unix_socket_path
        self._host = host
        self._port = port
        self._clients: dict[int, redis.Redis] = {}
        self._client: Optional[redis.Redis] = None
        self._cas_sha: Optional[str] = None
        self._decay_sha: Optional[str] = None
        self._deposit_sha: Optional[str] = None

    async def _connect(self) -> redis.Redis:
        loop_id = id(asyncio.get_running_loop())
        if loop_id in self._clients:
            self._client = self._clients[loop_id]
            return self._clients[loop_id]
        if self._path and Path(self._path).exists():
            client = redis.Redis(unix_socket_path=str(self._path), decode_responses=False)
        else:
            client = redis.Redis(
                host=self._host or settings.transport.valkey_host,
                port=self._port or settings.transport.valkey_port,
                decode_responses=False,
            )
        self._cas_sha = await client.script_load(LUA_CAS)
        self._decay_sha = await client.script_load(LUA_DECAY)
        self._deposit_sha = await client.script_load(LUA_DEPOSIT)
        self._clients[loop_id] = client
        self._client = client
        return client

    @property
    async def conn(self) -> redis.Redis:  # pragma: no cover - convenience property
        return await self._connect()

    # --- CAS / decay / deposit -------------------------------------------------
    async def cas(self, key: str, expected_ver: int, fields: dict[str, str]) -> tuple[int, int]:
        c = await self._connect()
        args = [str(expected_ver)]
        for k, v in fields.items():
            args += [k, v]
        result = await c.evalsha(self._cas_sha, 1, key, *args)
        return int(result[0]), int(result[1])

    async def decay(self, key: str, rho: float, hi: float, lo: float) -> float:
        c = await self._connect()
        out = await c.evalsha(self._decay_sha, 1, key, str(rho), str(hi), str(lo))
        return float(out)

    async def deposit(
        self,
        key: str,
        *,
        tau_delta: float,
        bel: float,
        pl: float,
        K: float,
        sensor: str,
        tau_max: float,
        now_ns: int,
    ) -> float:
        c = await self._connect()
        out = await c.evalsha(
            self._deposit_sha,
            1,
            key,
            str(tau_delta),
            str(bel),
            str(pl),
            str(K),
            sensor,
            str(tau_max),
            str(now_ns),
        )
        return float(out)

    # --- pass-through --------------------------------------------------------
    async def hgetall(self, key: str) -> dict[bytes, bytes]:
        c = await self._connect()
        return await c.hgetall(key)

    async def hset(self, key: str, field: str, value: str) -> int:
        c = await self._connect()
        return await c.hset(key, field, value)

    async def scan_iter(self, match: str, count: int = 500):
        c = await self._connect()
        async for k in c.scan_iter(match=match, count=count):
            yield k

    async def publish(self, channel: str, payload: bytes) -> int:
        c = await self._connect()
        return await c.publish(channel, payload)

    def pubsub(self):
        # PubSub requires a sync-style API — cheap to create per subscriber
        assert self._client, "call _connect() before pubsub()"
        return self._client.pubsub()

    async def close(self) -> None:
        for client in list(self._clients.values()):
            await client.aclose()
        self._clients.clear()
        self._client = None

    # pipeline passthrough — used by decay worker in hot loop
    def pipeline(self, transaction: bool = False):
        assert self._client, "call _connect() before pipeline()"
        return self._client.pipeline(transaction=transaction)


# Global singleton
valkey_client = ValkeyClient(unix_socket_path=settings.transport.valkey_sock)


async def get_valkey() -> ValkeyClient:
    await valkey_client._connect()  # noqa: SLF001
    return valkey_client


# -- canonical key helpers --------------------------------------------------
def pher_ip_key(addr: str) -> str:
    return f"pher:ip:{addr}"


def pher_hash_key(sha256: str) -> str:
    return f"pher:hash:{sha256}"


def pher_domain_key(domain: str) -> str:
    return f"pher:domain:{domain}"


def pher_process_key(host: str, pid: int) -> str:
    return f"pher:proc:{host}:{pid}"
