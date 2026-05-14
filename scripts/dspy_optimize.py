#!/usr/bin/env python3
"""DSPy optimizer — search scoped-prompt templates against a held-out set.

Per blueprint Part 9.5, the fractal pivot prompt is the single biggest lever for
precision at fixed recall. We use DSPy's BootstrapFewShot / MIPROv2 optimizer
against a ground-truth fixture of (exhibit_list, expected_technique) pairs.

This script is meant to run OFFLINE on a workstation; the resulting best prompt
is saved to `/opt/findevil/data/dspy/best_prompt.txt` and loaded by
`findevil.fractal.scoped_prompt.build_scoped_prompt` if present.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=Path, required=True, help="JSONL with {exhibits, technique}")
    ap.add_argument("--out", type=Path, default=Path("/opt/findevil/data/dspy/best_prompt.txt"))
    ap.add_argument("--iters", type=int, default=64)
    args = ap.parse_args()

    try:
        import dspy  # noqa: F401
    except ImportError:
        print("dspy-ai not installed; this optimizer is a no-op.")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("(dspy unavailable at optimize time)\n")
        return

    # Placeholder — real optimization requires a DSPy program definition mirroring
    # `scoped_prompt.build_scoped_prompt`. Intentionally left as a hook the operator
    # fills in based on the available fixture; we do not silently invent labels.
    args.out.parent.mkdir(parents=True, exist_ok=True)
    train = [json.loads(x) for x in args.train.read_text().splitlines() if x.strip()]
    args.out.write_text(f"# DSPy hook; n_train={len(train)}\n")
    print(f"wrote stub {args.out}")


if __name__ == "__main__":
    main()
