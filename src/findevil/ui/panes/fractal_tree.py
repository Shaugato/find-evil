"""Fractal spawn/report tree pane — live H3 graph."""

from __future__ import annotations

from textual.widgets import Tree


class FractalTreePane(Tree):
    def __init__(self, *args, **kwargs):
        super().__init__("fractal spawns", *args, **kwargs)
        self._nodes: dict[str, object] = {}

    def add_spawn(self, spawn: dict) -> None:
        parent_id = spawn.get("parent_id")
        label = (
            f"{spawn.get('spawn_id', '??')[:8]} "
            f"seed={spawn.get('seed_technique', '?')} "
            f"d={spawn.get('depth', 0)}"
        )
        parent = self._nodes.get(parent_id, self.root) if parent_id else self.root
        node = parent.add(label)  # type: ignore[attr-defined]
        self._nodes[spawn.get("spawn_id", "")] = node

    def mark_report(self, report: dict) -> None:
        node = self._nodes.get(report.get("spawn_id", ""))
        if node is None:
            return
        tag = "ttl" if report.get("terminated_by_ttl") else (
            "ok" if report.get("ok") else "err"
        )
        try:
            node.set_label(f"{node.label} [{tag}]")  # type: ignore[attr-defined]
        except Exception:
            pass
