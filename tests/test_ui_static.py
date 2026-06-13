from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_dashboard_root_serves_designed_live_shell(_temp_findevil_root: Path) -> None:
    from findevil.ui.http import app

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "AUTONOMOUS DFIR COMMAND SHELL" in response.text
    assert "/static/find-evil-live.js" in response.text
    assert "pheromone-canvas" in response.text
    assert "threat-graph-canvas" in response.text


def test_legacy_operator_guide_still_available(_temp_findevil_root: Path) -> None:
    from findevil.ui.http import app

    response = TestClient(app).get("/guide")

    assert response.status_code == 200
    assert "Stigmergy Operator Dashboard" in response.text


def test_live_adapter_preserves_design_renderers() -> None:
    adapter = Path("src/findevil/ui/static/find-evil-live.js").read_text(encoding="utf-8")

    assert "initThreatGraphCanvas = function" not in adapter
    assert "initPheromoneCanvas = function" not in adapter
    assert "renderAgents = function" not in adapter
    assert "renderIOCs = function" not in adapter
    assert "renderLedger = function" not in adapter
    assert "renderDebate = function" not in adapter
