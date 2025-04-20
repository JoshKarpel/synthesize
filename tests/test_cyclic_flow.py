from __future__ import annotations

from tests.conftest import run_example


def test_cyclic_flow_detection() -> None:
    result = run_example("cyclic.yaml")

    assert result.exit_code == 1

    assert "a -> b -> c -> a" in result.stdout
