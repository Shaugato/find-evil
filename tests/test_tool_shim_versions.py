from __future__ import annotations

import os
from pathlib import Path

import pytest

from findevil.tools.registry import resolve


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable bit required")
@pytest.mark.asyncio
async def test_sift_version_shims_execute_real_subprocess_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for name in ("vol", "yara", "zeek", "fls"):
        exe = tmp_path / name
        exe.write_text("#!/bin/sh\necho \"$0 version-ok\"\n", encoding="utf-8")
        exe.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))

    for tool in (
        "volatility.version",
        "yara.version",
        "zeek.version",
        "tsk.fls_version",
    ):
        fn = resolve(tool)
        assert fn is not None
        out = await fn([])
        assert out["ok"] is True
        assert "version-ok" in out["stdout"]
