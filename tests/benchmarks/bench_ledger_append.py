from __future__ import annotations

import argparse
import statistics
import tempfile
import time
from pathlib import Path

import blake3
import nacl.signing

from findevil.config.settings import settings
from findevil.ledger.schema import ArtifactRef, ArtifactType, ReasoningMethod, ReasoningStep, Severity
from findevil.ledger.writer import LedgerWriter


def pct(values: list[float], q: float) -> float:
    values = sorted(values)
    return values[min(len(values) - 1, int((len(values) - 1) * q))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=1_000)
    args = ap.parse_args()

    model_hash = blake3.blake3(b"bench.ledger").hexdigest()
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
            samples_us: list[float] = []
            for i in range(args.events):
                artifact = ArtifactRef(
                    type=ArtifactType.DOMAIN,
                    uri=f"domain-name:bench-{i}.invalid",
                )
                t0 = time.perf_counter_ns()
                writer.append(
                    agent_id="bench.ledger",
                    agent_version="0.1.0",
                    agent_model_hash=model_hash,
                    host_id=settings.host_id,
                    evidence_refs=[artifact],
                    primary_artifact_key=artifact.uri,
                    confidence=0.5,
                    severity=Severity.MEDIUM,
                    reasoning_trace=[
                        ReasoningStep(
                            step_index=0,
                            claim="Benchmark ledger append",
                            method=ReasoningMethod.STATISTICAL_ANOM,
                            confidence=0.5,
                        )
                    ],
                )
                samples_us.append((time.perf_counter_ns() - t0) / 1_000)
        finally:
            writer.close()

    print(f"Ledger append p50={statistics.median(samples_us):.2f}us p99={pct(samples_us, 0.99):.2f}us events={args.events}")


if __name__ == "__main__":
    main()
