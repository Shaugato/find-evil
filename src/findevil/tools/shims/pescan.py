"""Static PE inspection via `pefile` — no shelling out."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from findevil.tools.registry import register

from ._subprocess import first_target


@register("pescan.static")
async def static_scan(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    path = t.get("path") or t.get("value")
    if not path or not Path(path).exists():
        return {"ok": False, "error": f"file not found: {path}"}
    try:
        import pefile
    except ImportError as e:
        return {"ok": False, "error": f"pefile unavailable: {e}"}
    data = Path(path).read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()
    try:
        pe = pefile.PE(data=data, fast_load=False)
        sections = [
            {
                "name": s.Name.decode(errors="replace").rstrip("\x00"),
                "vsize": s.Misc_VirtualSize,
                "rsize": s.SizeOfRawData,
                "entropy": s.get_entropy(),
                "characteristics": hex(s.Characteristics),
            }
            for s in pe.sections
        ]
        imports = []
        if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                imports.append(
                    {
                        "dll": entry.dll.decode(errors="replace"),
                        "symbols": [
                            (imp.name.decode(errors="replace") if imp.name else f"ord_{imp.ordinal}")
                            for imp in entry.imports
                        ][:64],
                    }
                )
        suspicious = []
        if any(s["entropy"] > 7.5 for s in sections):
            suspicious.append("high-entropy section (likely packed)")
        if pe.OPTIONAL_HEADER.AddressOfEntryPoint == 0:
            suspicious.append("zero entry point")
        return {
            "ok": True,
            "sha256": sha256,
            "sections": sections,
            "imports": imports,
            "entry_point": hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),
            "suspicious": suspicious,
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "sha256": sha256}
