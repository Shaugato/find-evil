from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import time

import redis.asyncio as redis

from findevil.config.settings import settings


def pct(values: list[float], q: float) -> float:
    values = sorted(values)
    return values[min(len(values) - 1, int((len(values) - 1) * q))]


async def run(events: int) -> None:
    key = f"bench:valkey:{os.getpid()}"
    r = redis.Redis(unix_socket_path=str(settings.transport.valkey_sock), decode_responses=False)
    await r.ping()
    for _ in range(200):
        await r.hset(key, mapping={"tau": "0.1", "bel_evil": "0.5"})

    samples_us: list[float] = []
    for i in range(events):
        t0 = time.perf_counter_ns()
        await r.hset(
            key,
            mapping={
                "tau": f"{i / events:.6f}",
                "bel_evil": "0.500000",
                "pl_evil": "0.700000",
                "conflict_K": "0.000000",
                "sensor_diversity": "1",
            },
        )
        samples_us.append((time.perf_counter_ns() - t0) / 1_000)
    await r.delete(key)
    await r.aclose()
    print(f"Valkey UDS HSET p50={statistics.median(samples_us):.2f}us p99={pct(samples_us, 0.99):.2f}us events={events}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=10_000)
    args = ap.parse_args()
    asyncio.run(run(args.events))


if __name__ == "__main__":
    main()
