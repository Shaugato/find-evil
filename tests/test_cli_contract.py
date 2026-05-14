from __future__ import annotations

from typer.testing import CliRunner

from findevil.cli import cli


def test_implementation_guide_cli_aliases_are_registered() -> None:
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "ledger-tip" in result.output
    assert "demo-tui" in result.output
    assert "nats-setup" in result.output
