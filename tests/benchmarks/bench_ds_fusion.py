from __future__ import annotations

import argparse
import statistics
import time

from findevil.swarm.ds_fusion import AgentReport, fuse


def pct(values: list[float], q: float) -> float:
    values = sorted(values)
    return values[min(len(values) - 1, int((len(values) - 1) * q))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=50_000)
    args = ap.parse_args()
    reports = [
        AgentReport("yara_agent", confidence=0.91, reliability=0.95),
        AgentReport("edr_agent", confidence=0.83, reliability=0.90),
        AgentReport("volatility", confidence=0.76, reliability=0.85),
    ]

    for _ in range(1_000):
        fuse(reports)

    samples_us: list[float] = []
    for _ in range(args.events):
        t0 = time.perf_counter_ns()
        fuse(reports)
        samples_us.append((time.perf_counter_ns() - t0) / 1_000)

    print(f"D-S fusion 3-agent p50={statistics.median(samples_us):.2f}us p99={pct(samples_us, 0.99):.2f}us events={args.events}")


if __name__ == "__main__":
    main()
