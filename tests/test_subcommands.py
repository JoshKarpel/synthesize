from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from synthesize.cli import cli

EXAMPLES_DIR = Path(__file__).parent.parent / "docs" / "examples"


def test_list_outputs_flow_names() -> None:
    result = CliRunner().invoke(cli, ["list", "--config", str(EXAMPLES_DIR / "after.yaml")])

    assert result.exit_code == 0
    assert "default" in result.output


def test_list_multiple_flows(tmp_path: Path) -> None:
    config_file = tmp_path / "synth.yaml"
    config_file.write_text("flows:\n  build: {}\n  check: {}\n  dev: {}")

    result = CliRunner().invoke(cli, ["list", "--config", str(config_file)])

    assert result.exit_code == 0
    assert result.output.splitlines() == ["build *", "check", "dev"]


def test_list_marks_flow_named_default_as_default(tmp_path: Path) -> None:
    config_file = tmp_path / "synth.yaml"
    config_file.write_text("flows:\n  build: {}\n  default: {}\n  dev: {}")

    result = CliRunner().invoke(cli, ["list", "--config", str(config_file)])

    assert result.exit_code == 0
    assert result.output.splitlines() == ["build", "default *", "dev"]


def test_list_marks_default_flow_setting_as_default(tmp_path: Path) -> None:
    config_file = tmp_path / "synth.yaml"
    config_file.write_text("settings:\n  default_flow: dev\nflows:\n  build: {}\n  default: {}\n  dev: {}")

    result = CliRunner().invoke(cli, ["list", "--config", str(config_file)])

    assert result.exit_code == 0
    assert result.output.splitlines() == ["build", "default", "dev *"]


def test_list_shows_no_default_marker_when_default_flow_does_not_exist(tmp_path: Path) -> None:
    config_file = tmp_path / "synth.yaml"
    config_file.write_text("settings:\n  default_flow: nonexistent\nflows:\n  build: {}\n  dev: {}")

    result = CliRunner().invoke(cli, ["list", "--config", str(config_file)])

    assert result.exit_code == 0
    assert result.output.splitlines() == ["build", "dev"]


def test_run_errors_when_default_flow_does_not_exist(tmp_path: Path) -> None:
    config_file = tmp_path / "synth.yaml"
    config_file.write_text("settings:\n  default_flow: nonexistent\nflows:\n  build: {}\n  dev: {}")

    result = CliRunner().invoke(cli, ["run", "--config", str(config_file)])

    assert result.exit_code == 1
    assert "failed to determine a default flow" in result.output


def test_list_shows_description(tmp_path: Path) -> None:
    config_file = tmp_path / "synth.yaml"
    config_file.write_text("flows:\n  check:\n    description: run tests and lint\n  dev: {}")

    result = CliRunner().invoke(cli, ["list", "--config", str(config_file)])

    assert result.exit_code == 0
    assert "check" in result.output
    assert "run tests and lint" in result.output
    assert "dev" in result.output


def test_list_details_shows_nodes(tmp_path: Path) -> None:
    config_file = tmp_path / "synth.yaml"
    config_file.write_text(
        "flows:\n  check:\n    nodes:\n      lint:\n        recipe:\n          commands: ruff check ."
    )

    result = CliRunner().invoke(cli, ["list", "--details", "--config", str(config_file)])

    assert result.exit_code == 0
    assert "check" in result.output
    assert "lint" in result.output
    assert "ruff check ." in result.output


def test_diagram_outputs_diagram() -> None:
    result = CliRunner().invoke(cli, ["diagram", "--config", str(EXAMPLES_DIR / "after.yaml")])

    assert result.exit_code == 0
    assert "flowchart" in result.output


def test_diagram_unknown_flow_exits_with_error() -> None:
    result = CliRunner().invoke(cli, ["diagram", "nonexistent", "--config", str(EXAMPLES_DIR / "after.yaml")])

    assert result.exit_code == 1
