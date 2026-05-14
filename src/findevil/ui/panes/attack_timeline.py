"""ATT&CK kill-chain pane — reads bb://attack/current_path."""

from __future__ import annotations

from textual.widgets import Static


class AttackTimelinePane(Static):
    def render(self) -> str:  # type: ignore[override]
        chain = getattr(self, "_chain", [])
        if not chain:
            return "[dim]no techniques yet[/dim]"
        return " → ".join(f"[b]{t}[/b]" for t in chain)

    def update_chain(self, techniques: list[str]) -> None:
        self._chain = techniques
        self.refresh()
