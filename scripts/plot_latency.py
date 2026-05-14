#!/usr/bin/env python3
"""Plot detection/mitigation latency from red-team results jsonl.

Reads `/opt/findevil/data/redteam_results.jsonl` (or --input) and writes a PNG
histogram + a per-technique box plot. Matplotlib-only; no seaborn.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=Path("/opt/findevil/data/redteam_results.jsonl"))
    ap.add_argument("--out", type=Path, default=Path("/opt/findevil/data/redteam_latency.png"))
    args = ap.parse_args()

    by_tech: dict[str, list[float]] = defaultdict(list)
    mit_lat: list[float] = []
    for line in args.input.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        tech = rec.get("technique", "?")
        det = rec.get("detection", {})
        mit = rec.get("mitigation", {})
        if isinstance(det, dict) and det.get("detected"):
            by_tech[tech].append(float(det.get("detection_latency_ms", 0.0)))
        if isinstance(mit, dict) and mit.get("mitigated"):
            mit_lat.append(float(mit.get("mitigation_latency_ms", 0.0)))

    if not by_tech and not mit_lat:
        print("no latencies to plot")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    if by_tech:
        ax1.boxplot(by_tech.values(), labels=list(by_tech.keys()))
        ax1.set_title("detection latency per ATT&CK (ms)")
        ax1.set_yscale("log")
        ax1.tick_params(axis="x", rotation=45)
    if mit_lat:
        ax2.hist(mit_lat, bins=40)
        ax2.set_title(f"mitigation latency (n={len(mit_lat)}) ms")
        ax2.set_xlabel("ms")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(args.out, dpi=120)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
