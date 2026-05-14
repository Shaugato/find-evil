"""Ledger tip pane — shows seq, entry_hash, latest anchor Merkle root."""

from __future__ import annotations

from textual.widgets import Static


class LedgerTipPane(Static):
    def render(self) -> str:  # type: ignore[override]
        tip = getattr(self, "_tip", None)
        if tip is None:
            return "[dim]waiting for ledger...[/dim]"
        return (
            f"[b]seq[/b] {tip.get('seq', 0)}   "
            f"[b]hash[/b] {str(tip.get('entry_hash') or '')[:12]}…   "
            f"[b]merkle[/b] {str(tip.get('last_merkle_root') or '')[:12]}…   "
            f"[b]rekor[/b] {tip.get('last_rekor_log_index', '-')}"
        )

    def update_tip(self, tip: dict) -> None:
        self._tip = tip
        self.refresh()
