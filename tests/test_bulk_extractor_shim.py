"""bulk_extractor MCP shim — version + bounded scan summary (Part 12)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from findevil.tools.registry import resolve

FAKE_BE = """#!/bin/sh
# Fake bulk_extractor: mimics `-o outdir ... image` by writing feature files.
if [ "$1" = "-V" ]; then
  echo "bulk_extractor 2.1.1"
  exit 0
fi
outdir=""
while [ $# -gt 1 ]; do
  if [ "$1" = "-o" ]; then outdir="$2"; shift 2; else shift; fi
done
mkdir -p "$outdir"
printf '# BANNER\\n10.0.0.1\\t10.0.0.1\\tstruct ip\\n' > "$outdir/ip.txt"
printf 'http://evil.example/payload\\thttp://evil.example/payload\\n' > "$outdir/url.txt"
touch "$outdir/email.txt"
echo "scan complete"
"""


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable bit required")
@pytest.mark.asyncio
async def test_bulk_extractor_version(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    exe = tmp_path / "bulk_extractor"
    exe.write_text(FAKE_BE, encoding="utf-8")
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))

    fn = resolve("bulk_extractor.version")
    assert fn is not None
    out = await fn([])
    assert out["ok"] is True
    assert "bulk_extractor 2.1.1" in out["stdout"]


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable bit required")
@pytest.mark.asyncio
async def test_bulk_extractor_scan_summarises_features(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    exe = tmp_path / "bulk_extractor"
    exe.write_text(FAKE_BE, encoding="utf-8")
    exe.chmod(0o755)
    # Keep system bins on PATH — the fake script needs mkdir/touch.
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")
    monkeypatch.setenv("FINDEVIL_TOOL_CACHE_DIR", str(tmp_path / "cache"))

    image = tmp_path / "evidence.raw"
    image.write_bytes(b"\x00" * 64)

    fn = resolve("bulk_extractor.scan")
    assert fn is not None
    out = await fn([{"target": {"image": str(image)}}])
    assert out["ok"] is True, out
    assert out["outdir"].startswith(str(tmp_path / "cache"))

    features = out["features"]
    # Comment banner lines are stripped; empty email.txt is skipped.
    assert "ip.txt" in features and features["ip.txt"]["feature_count"] == 1
    assert features["ip.txt"]["head"][0].startswith("10.0.0.1")
    assert "url.txt" in features
    assert "email.txt" not in features


@pytest.mark.asyncio
async def test_bulk_extractor_scan_rejects_missing_image():
    fn = resolve("bulk_extractor.scan")
    assert fn is not None
    out = await fn([{"target": {}}])
    assert out["ok"] is False
    out2 = await fn([{"target": {"image": "/nonexistent/evidence.raw"}}])
    assert out2["ok"] is False
