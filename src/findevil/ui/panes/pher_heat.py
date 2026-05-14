"""Pheromone heatmap pane — renders top-N τ values by kind."""

from __future__ import annotations

from textual.widgets import DataTable, Static


class PheromoneHeatPane(Static):
    rows_to_show = 20

    def compose(self):  # type: ignore[override]
        yield DataTable(id="pher-table", zebra_stripes=True)

    def on_mount(self) -> None:
        table = self.query_one("#pher-table", DataTable)
        table.add_columns("kind", "key", "τ", "bel", "K", "div")

    def refresh_rows(self, snapshots: list[dict]) -> None:
        table = self.query_one("#pher-table", DataTable)
        table.clear()
        for s in snapshots[: self.rows_to_show]:
            table.add_row(
                s.get("kind", "-"),
                s.get("key", "-")[-36:],
                f"{float(s.get('tau', 0.0)):.2f}",
                f"{float(s.get('bel_evil', 0.0)):.2f}",
                f"{float(s.get('conflict_K', 0.0)):.2f}",
                str(s.get("sensor_diversity", 0)),
            )
