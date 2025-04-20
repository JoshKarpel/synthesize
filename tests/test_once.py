from __future__ import annotations

from typer.testing import CliRunner

from tests.conftest import run_example

runner = CliRunner()


def test_once_flag_terminates_watch_flow() -> None:
    result = run_example("watch.yaml", ("--once",))

    assert result.exit_code == 0
