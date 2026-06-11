"""bulk_extractor shims — stream-carving feature extraction over images.

bulk_extractor scans a disk/memory image without filesystem parsing and
emits feature files (emails, urls, domains, ccns, …). The scan shim runs it
into a fresh tool-cache directory and returns a bounded summary of the
feature files so the LLM plane never receives multi-MB raw output.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from findevil.tools.registry import register

from ._subprocess import first_arg, first_target, run_cmd

# Feature files worth summarising, in priority order.
_INTERESTING = (
    "email.txt",
    "url.txt",
    "domain.txt",
    "ip.txt",
    "exif.txt",
    "ccn.txt",
    "telephone.txt",
    "rfc822.txt",
    "windirs.txt",
    "winpe.txt",
)
_MAX_LINES_PER_FILE = 20
_MAX_TOTAL_LINES = 80


@register("bulk_extractor.version")
async def version(_commands: list[dict]) -> dict[str, Any]:
    return await run_cmd(["bulk_extractor", "-V"], timeout_s=20.0)


def _summarise_outdir(outdir: Path) -> dict[str, Any]:
    features: dict[str, Any] = {}
    total = 0
    for fname in _INTERESTING:
        fp = outdir / fname
        if not fp.is_file() or fp.stat().st_size == 0:
            continue
        lines: list[str] = []
        with fp.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("#"):
                    continue
                lines.append(line.rstrip("\n"))
                if (
                    len(lines) >= _MAX_LINES_PER_FILE
                    or total + len(lines) >= _MAX_TOTAL_LINES
                ):
                    break
        if lines:
            count = sum(
                1
                for line in fp.open(encoding="utf-8", errors="replace")
                if not line.startswith("#")
            )
            features[fname] = {"feature_count": count, "head": lines}
            total += len(lines)
        if total >= _MAX_TOTAL_LINES:
            break
    return features


@register("bulk_extractor.scan")
async def scan(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    image = t.get("image") or t.get("value")
    if not image:
        return {"ok": False, "error": "missing target.image"}
    if not Path(image).is_file():
        return {"ok": False, "error": f"image not found: {image}"}

    cache_root = Path(
        os.environ.get("FINDEVIL_TOOL_CACHE_DIR", "/opt/findevil/data/tool-cache")
    )
    # bulk_extractor refuses to write into an existing directory — always mint
    # a fresh one under the sandboxed tool cache.
    outdir = cache_root / "bulk_extractor" / f"{Path(image).stem}-{time.time_ns()}"
    outdir.parent.mkdir(parents=True, exist_ok=True)

    argv = ["bulk_extractor", "-o", str(outdir)]
    scanners = first_arg(commands, "scanners")
    if scanners:
        # -x all + -e <scanner> keeps runs bounded to what was asked for.
        argv += ["-x", "all"]
        for s in scanners:
            argv += ["-e", str(s)]
    argv.append(image)

    timeout_s = float(first_arg(commands, "timeout_s", 600.0))
    result = await run_cmd(argv, timeout_s=timeout_s)
    if not result["ok"]:
        return result

    result["outdir"] = str(outdir)
    result["features"] = _summarise_outdir(outdir)
    # Raw stdout from bulk_extractor is progress chatter; keep only the tail.
    result["stdout"] = "\n".join(result["stdout"].splitlines()[-15:])
    return result
