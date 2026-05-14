"""Consensus live feed — subscribes to `findevil.shadow.consensus`."""

from __future__ import annotations

import json

from textual.reactive import reactive
from textual.widgets import DataTable, Static


class ConsensusFeedPane(Static):
    """Scrolling table of the last ~50 consensus frames."""

    max_rows = 50
    rows = reactive(list, always_update=True)

    def compose(self):  # type: ignore[override]
        yield DataTable(id="consensus-table", zebra_stripes=True)

    def on_mount(self) -> None:
        table = self.query_one("#consensus-table", DataTable)
        table.add_columns("time", "kind", "key", "action", "bel", "K", "tau")

    def push_frame(self, frame: dict) -> None:
        table = self.query_one("#consensus-table", DataTable)
        if table.row_count >= self.max_rows:
            table.remove_row(table.get_row_at(0)[0] if table.rows else "")  # type: ignore[arg-type]
        table.add_row(
            str(frame.get("emitted_ts", "-")),
            str(frame.get("kind", "-")),
            str(frame.get("pher_key", "-"))[-28:],
            str(frame.get("action", "-")),
            f"{frame.get('belief_evil', 0.0):.2f}",
            f"{frame.get('conflict_K', 0.0):.2f}",
            f"{frame.get('tau', 0.0):.2f}",
        )

    def feed_message(self, raw: bytes) -> None:
        try:
            env = json.loads(raw)
            payload = env.get("payload")
            frame = json.loads(payload) if isinstance(payload, (str, bytes)) else env
        except ValueError:
            return
        self.push_frame(frame)
