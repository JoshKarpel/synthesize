from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from synthesize.cli import cli

runner = CliRunner()


def test_once_flag_terminates_watch_flow() -> None:
    example_path = Path(__file__).parent.parent / "docs" / "examples" / "watch.yaml"

    result = runner.invoke(cli, ["run", "--once", "--config", str(example_path)])

    assert result.exit_code == 0, f"Command failed with exit code {result.exit_code}: {result.stdout}"
