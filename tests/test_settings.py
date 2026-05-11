from __future__ import annotations

from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from synthesize.cli import Env, _make_console, cli
from tests.conftest import run_example


def test_synth_force_terminal_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYNTH_FORCE_TERMINAL", "true")
    assert _make_console(Env()).is_terminal is True


def test_synth_force_terminal_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYNTH_FORCE_TERMINAL", "false")
    assert _make_console(Env()).is_terminal is False


def test_synth_force_terminal_missing_auto_detects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SYNTH_FORCE_TERMINAL")
    console = _make_console(Env())
    assert console.is_terminal is False  # no tty in test process


def test_synth_force_terminal_invalid_exits_with_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "synth.yaml"
    config_file.write_text("flows:\n  default: {}")
    monkeypatch.setenv("SYNTH_FORCE_TERMINAL", "not-a-bool")

    result = CliRunner().invoke(cli, ["run", "--config", str(config_file), "--dry"])

    assert result.exit_code == 1
    assert "force_terminal" in result.output


def test_synth_file_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "synth.yaml"
    config_file.write_text("flows:\n  default: {}")
    monkeypatch.setenv("SYNTH_FILE", str(config_file))

    result = CliRunner().invoke(cli, ["run", "--dry"])

    assert result.exit_code == 0


def test_synth_file_env_var_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "synth.yaml"
    config_file.write_text("flows:\n  default: {}")
    monkeypatch.setenv("SYNTH_FILE", str(config_file))

    result = CliRunner().invoke(cli, ["list"])

    assert result.exit_code == 0


def test_synth_file_env_var_diagram(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "synth.yaml"
    config_file.write_text("flows:\n  default: {}")
    monkeypatch.setenv("SYNTH_FILE", str(config_file))

    result = CliRunner().invoke(cli, ["diagram"])

    assert result.exit_code == 0


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
