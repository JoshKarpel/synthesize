from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from synthesize.cli import cli


@pytest.fixture(autouse=True)
def clean_env_var() -> Iterator[None]:
    os.environ.pop("SYNTH_TEST_VAR", None)
    yield
    os.environ.pop("SYNTH_TEST_VAR", None)


def test_env_var_from_dot_env_available_in_recipe(tmp_path: Path) -> None:
    config_file = tmp_path / "synth.yaml"
    config_file.write_text("""
flows:
  default:
    nodes:
      echo:
        recipe:
          commands: echo $SYNTH_TEST_VAR
""")
    (tmp_path / ".env").write_text("SYNTH_TEST_VAR=hello_from_dotenv\n")

    result = CliRunner().invoke(cli, ["--config", str(config_file)])

    assert result.exit_code == 0
    assert "hello_from_dotenv" in result.stdout
