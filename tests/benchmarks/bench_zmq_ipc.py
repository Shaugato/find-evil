from __future__ import annotations

import argparse
import os
import statistics
import time

import msgspec
import zmq


def pct(values: list[float], q: float) -> float:
    values = sorted(values)
    return values[min(len(values) - 1, int((len(values) - 1) * q))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=10_000)
    args = ap.parse_args()

    ctx = zmq.Context.instance()
    endpoint = f"ipc:///tmp/findevil-bench-zmq-{os.getpid()}.sock"
    receiver = ctx.socket(zmq.PAIR)
    sender = ctx.socket(zmq.PAIR)
    receiver.bind(endpoint)
    sender.connect(endpoint)

    payload = {
        "event_id": "bench",
        "event_time_ns": time.time_ns(),
        "source": "sysmon",
        "indicator_key": "proc://bench-zmq",
        "confidence": 0.5,
        "artifact_type": "process",
    }

    for _ in range(200):
        sender.send(msgspec.json.encode(payload))
        receiver.recv()

    samples_us: list[float] = []
    for i in range(args.events):
        payload["event_id"] = f"bench-{i}"
        t0 = time.perf_counter_ns()
        sender.send(msgspec.json.encode(payload))
        receiver.recv()
        samples_us.append((time.perf_counter_ns() - t0) / 1_000)

    print(f"ZMQ IPC encode+roundtrip p50={statistics.median(samples_us):.2f}us p99={pct(samples_us, 0.99):.2f}us events={args.events}")
    sender.close(0)
    receiver.close(0)


if __name__ == "__main__":
    main()
