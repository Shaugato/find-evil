from __future__ import annotations

import argparse
import asyncio
import csv
import statistics
import tempfile
import time
from pathlib import Path

import blake3
import nacl.signing

from findevil.config.settings import settings
from findevil.ledger.schema import ArtifactRef, ArtifactType, ReasoningMethod, ReasoningStep, Severity
from findevil.ledger.writer import LedgerWriter
from findevil.swarm.ds_fusion import AgentReport, fuse
from findevil.transport.valkey import get_valkey


def pct(values: list[float], q: float) -> float:
    values = sorted(values)
    return values[min(len(values) - 1, int((len(values) - 1) * q))]


async def run(events: int, out: Path | None) -> None:
    vc = await get_valkey()
    conn = await vc._connect()  # noqa: SLF001
    key = f"bench:hot:{int(time.time())}"
    reports = [
        AgentReport("yara_agent", confidence=0.91, reliability=0.95, sensor="yara"),
        AgentReport("edr_agent", confidence=0.83, reliability=0.90, sensor="edr"),
        AgentReport("volatility", confidence=0.76, reliability=0.85, sensor="volatility"),
    ]
    rows: list[dict[str, float | int]] = []
    model_hash = blake3.blake3(b"bench.hot").hexdigest()
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        sk = nacl.signing.SigningKey.generate()
        sk_path = td_path / "ledger_ed25519.sk"
        pk_path = td_path / "ledger_ed25519.pk"
        sk_path.write_bytes(sk.encode())
        pk_path.write_bytes(sk.verify_key.encode())
        writer = LedgerWriter(
            sqlite_path=td_path / "ledger.sqlite",
            sk_path=sk_path,
            pk_path=pk_path,
        )
        try:
            for i in range(events):
                total0 = time.perf_counter_ns()

                t0 = time.perf_counter_ns()
                fused = fuse(reports)
                ds_us = (time.perf_counter_ns() - t0) / 1_000

                t0 = time.perf_counter_ns()
                await vc.deposit(
                    key,
                    tau_delta=max(0.01, fused["belief_evil"] - 0.5 * fused["uncertainty"]),
                    bel=fused["belief_evil"],
                    pl=fused["plausibility_evil"],
                    K=fused["conflict_K"],
                    sensor="bench",
                    tau_max=settings.swarm.tau_max,
                    now_ns=time.time_ns(),
                )
                valkey_us = (time.perf_counter_ns() - t0) / 1_000

                artifact = ArtifactRef(type=ArtifactType.PROCESS, uri=f"process:bench-{i}")
                t0 = time.perf_counter_ns()
                writer.append(
                    agent_id="bench.hot",
                    agent_version="0.1.0",
                    agent_model_hash=model_hash,
                    host_id=settings.host_id,
                    evidence_refs=[artifact],
                    primary_artifact_key=artifact.uri,
                    confidence=fused["belief_evil"],
                    severity=Severity.HIGH,
                    reasoning_trace=[
                        ReasoningStep(
                            step_index=0,
                            claim="Benchmark hot-path append",
                            method=ReasoningMethod.STATISTICAL_ANOM,
                            confidence=fused["belief_evil"],
                        )
                    ],
                )
                ledger_us = (time.perf_counter_ns() - t0) / 1_000
                total_us = (time.perf_counter_ns() - total0) / 1_000
                rows.append(
                    {
                        "i": i,
                        "ds_us": ds_us,
                        "valkey_us": valkey_us,
                        "ledger_us": ledger_us,
                        "total_us": total_us,
                    }
                )
        finally:
            writer.close()
            await conn.delete(key, f"{key}:sensors")
            await vc.close()

    if out is not None:
        with out.open("w", newline="") as f:
            writer_csv = csv.DictWriter(f, fieldnames=["i", "ds_us", "valkey_us", "ledger_us", "total_us"])
            writer_csv.writeheader()
            writer_csv.writerows(rows)

    totals_ms = [float(r["total_us"]) / 1_000 for r in rows]
    ledger_us = [float(r["ledger_us"]) for r in rows]
    ds_us = [float(r["ds_us"]) for r in rows]
    print(
        "Hot path temp-ledger p50="
        f"{statistics.median(totals_ms):.3f}ms p99={pct(totals_ms, 0.99):.3f}ms "
        f"ledger_p50={statistics.median(ledger_us):.2f}us ds_p50={statistics.median(ds_us):.2f}us "
        f"events={events}"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=1_000)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    asyncio.run(run(args.events, args.out))


if __name__ == "__main__":
    main()
