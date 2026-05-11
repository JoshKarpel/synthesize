from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from synthesize.cli import cli


@pytest.fixture(autouse=True)
def force_rich_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force Rich to always emit full terminal formatting in tests.

    Without this, Rich auto-detects terminal capabilities. Under bare pytest
    there's no tty so it emits no ANSI; under synth xdist workers inherit a
    pseudo-tty so it does. SYNTH_FORCE_TERMINAL makes test output
    consistent regardless of environment.
    """
    monkeypatch.setenv("SYNTH_FORCE_TERMINAL", "true")


EXAMPLES_DIR = Path(__file__).parent.parent / "docs" / "examples"


def run_example(example: str, extra_args: tuple[str, ...] = ()) -> Result:
    runner = CliRunner()
    example_path = EXAMPLES_DIR / example
    assert example_path.exists(), f"Example file {example_path} does not exist."

    result = runner.invoke(cli, ["run", "--config", str(example_path), *extra_args])

    print(result.stdout)

    return result
