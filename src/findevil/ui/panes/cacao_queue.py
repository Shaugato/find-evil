"""CACAO instance queue — reads `cacao:instance:*` keys for live playbooks."""

from __future__ import annotations

from textual.widgets import DataTable, Static


class CacaoQueuePane(Static):
    max_rows = 20

    def compose(self):  # type: ignore[override]
        yield DataTable(id="cacao-table", zebra_stripes=True)

    def on_mount(self) -> None:
        table = self.query_one("#cacao-table", DataTable)
        table.add_columns("instance", "playbook", "status", "cursor", "errors")

    def refresh_rows(self, instances: list[dict]) -> None:
        table = self.query_one("#cacao-table", DataTable)
        table.clear()
        for inst in instances[: self.max_rows]:
            table.add_row(
                inst.get("instance_id", "-")[:8],
                inst.get("playbook_id", "-")[:20],
                inst.get("status", "-"),
                str(inst.get("step_cursor", 0)),
                str(len(inst.get("errors", []))),
            )
