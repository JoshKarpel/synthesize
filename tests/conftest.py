from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner, Result

from synthesize.cli import cli

EXAMPLES_DIR = Path(__file__).parent.parent / "docs" / "examples"


def run_example(example: str, extra_args: tuple[str, ...] = ()) -> Result:
    runner = CliRunner()
    example_path = EXAMPLES_DIR / example
    assert example_path.exists(), f"Example file {example_path} does not exist."

    result = runner.invoke(cli, ["--config", str(example_path), *extra_args])

    print(result.stdout)

    return result
