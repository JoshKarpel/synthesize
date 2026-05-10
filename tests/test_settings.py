from __future__ import annotations

from pathlib import Path

from pytest_mock import MockerFixture
from typer.testing import CliRunner

from synthesize.cli import cli
from tests.conftest import run_example


def test_setting_override_accepted() -> None:
    result = run_example("once.yaml", ("--setting", "timestamps.sub_second_digits=3"))

    assert result.exit_code == 0


def test_invalid_setting_value_exits_with_error() -> None:
    result = run_example("once.yaml", ("--setting", "timestamps.sub_second_digits=99"))

    assert result.exit_code == 1


def test_malformed_setting_exits_with_error() -> None:
    result = run_example(
        "once.yaml",
        (
            "--setting",
            "no-equals-sign",
        ),
    )

    assert result.exit_code == 1


def test_dot_env_loaded_by_default(tmp_path: Path, mocker: MockerFixture) -> None:
    mock_load = mocker.patch("synthesize.cli.load_dotenv")
    config_file = tmp_path / "synth.yaml"
    config_file.write_text("flows:\n  default: {}")

    result = CliRunner().invoke(cli, ["run", "--config", str(config_file), "--dry"])

    assert result.exit_code == 0
    mock_load.assert_called_once_with(tmp_path / ".env")


def test_dot_env_loading_disabled_via_setting(tmp_path: Path, mocker: MockerFixture) -> None:
    mock_load = mocker.patch("synthesize.cli.load_dotenv")
    config_file = tmp_path / "synth.yaml"
    config_file.write_text("flows:\n  default: {}")

    result = CliRunner().invoke(cli, ["run", "--config", str(config_file), "--dry", "--setting", "dot_env.load=false"])

    assert result.exit_code == 0
    mock_load.assert_not_called()


def test_dot_env_file_customized_via_setting(tmp_path: Path, mocker: MockerFixture) -> None:
    mock_load = mocker.patch("synthesize.cli.load_dotenv")
    config_file = tmp_path / "synth.yaml"
    config_file.write_text("flows:\n  default: {}")

    result = CliRunner().invoke(
        cli, ["run", "--config", str(config_file), "--dry", "--setting", "dot_env.file=.custom-env"]
    )

    assert result.exit_code == 0
    mock_load.assert_called_once_with(tmp_path / ".custom-env")
