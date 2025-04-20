from __future__ import annotations

from typer.testing import CliRunner

from tests.conftest import run_example

runner = CliRunner()


def test_if_all_commands_succeed_exit_code_is_0() -> None:
    result = run_example("after.yaml")

    assert result.exit_code == 0


def test_if_some_commands_fail_or_dont_run_exit_code_is_1() -> None:
    result = run_example("after-with-failure.yaml")

    assert result.exit_code == 1
