"""Stigmergic pheromone decay worker.

Blueprint Part 7.1.1: tau(t+1) = (1 - rho_decay) * tau(t) + deposits.
Runs as a long-lived asyncio task on `tick_ms` period. Decay applies only when
Bel(evil) < 0.15; otherwise the pheromone reinforces itself.

Also enforces MAX-MIN bounds to prevent low-and-slow adversarial gaming, and emits
a long-window cumulative-delta z-score detector.
"""

from __future__ import annotations

import anyio
import numpy as np

from findevil.config.settings import settings
from findevil.transport.valkey import ValkeyClient, get_valkey

# Sliding window for cumulative Δτ z-score alarms (per-key, cheap)
_DELTA_WINDOW: dict[str, list[float]] = {}
_DELTA_WINDOW_MAX = 64
_Z_THRESHOLD = 3.5


async def _zscore_alarm(key: str, delta: float) -> bool:
    w = _DELTA_WINDOW.setdefault(key, [])
    w.append(delta)
    if len(w) > _DELTA_WINDOW_MAX:
        w.pop(0)
    if len(w) < 16:
        return False
    arr = np.asarray(w)
    mu, sigma = float(arr.mean()), float(arr.std())
    if sigma < 1e-6:
        return False
    return abs(delta - mu) / sigma > _Z_THRESHOLD


async def decay_tick(vc: ValkeyClient) -> int:
    """Run one decay pass over every pher:* key. Returns #keys touched."""
    touched = 0
    async for raw_key in vc.scan_iter(match="pher:*", count=500):
        if isinstance(raw_key, bytes):
            key = raw_key.decode()
        else:
            key = raw_key
        # Skip internal sets (sensors, history)
        if key.endswith(":sensors") or ":history" in key:
            continue
        old = 0.0
        state = await vc.hgetall(key)
        if state:
            try:
                old = float(state.get(b"tau", b"0"))
                bel = float(state.get(b"bel_evil", b"0"))
                if bel >= 0.15:
                    # Reinforcing; skip decay
                    continue
            except ValueError:
                pass
        new_tau = await vc.decay(
            key,
            settings.swarm.decay_rho,
            settings.swarm.tau_max,
            settings.swarm.tau_min,
        )
        touched += 1
        delta = new_tau - old
        if await _zscore_alarm(key, delta):
            # Alert via Prometheus counter (wired in observability.metrics)
            from findevil.observability.metrics import LONG_WINDOW_ZSCORE_ALERTS

            LONG_WINDOW_ZSCORE_ALERTS.labels(key=key).inc()
    return touched


async def run_forever() -> None:
    vc = await get_valkey()
    interval = settings.swarm.tick_ms / 1000.0
    while True:
        try:
            await decay_tick(vc)
        except Exception:  # keep the worker alive — log via structlog
            import structlog

            structlog.get_logger("findevil.swarm.decay").exception("decay_tick failed")
        await anyio.sleep(interval)


if __name__ == "__main__":  # pragma: no cover
    anyio.run(run_forever)
