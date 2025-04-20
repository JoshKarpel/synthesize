from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

runner = CliRunner()


def test_once_flag_terminates_watch_flow() -> None:
    example_path = Path(__file__).parent.parent / "docs" / "examples" / "watch.yaml"

    process = subprocess.run(
        [sys.executable, "-m", "synthesize.cli", "run", "--once", "--config", str(example_path)],
        timeout=5,
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 0, f"Process failed with exit code {process.returncode}: {process.stdout}"

    assert "A" in process.stdout
    assert "B" in process.stdout
