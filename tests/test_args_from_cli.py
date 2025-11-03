from __future__ import annotations

import pytest
from typer.testing import CliRunner

from tests.conftest import run_example

runner = CliRunner()


@pytest.mark.parametrize(
    ("cli_args", "expected"),
    (
        ((), ("a b", "c d")),
        (
            (
                "--arg",
                "arg=foo",  # This doesn't work because node args still override
            ),
            ("a b", "c d"),
        ),
        (
            (
                "--arg",
                "a.arg=foo",
            ),
            ("foo b", "c d"),
        ),
        (
            (
                "--env",
                "ENV=foo",  # This doesn't work because node envs still override
            ),
            ("a b", "c d"),
        ),
        (
            (
                "--env",
                "a.ENV=foo",
            ),
            ("a foo", "c d"),
        ),
    ),
)
def test_inject_args_and_envs_from_cli(cli_args: tuple[str, ...], expected: tuple[str, ...]) -> None:
    result = run_example("args_and_envs.yaml", cli_args)

    assert result.exit_code == 0

    for e in expected:
        assert e in result.stdout
