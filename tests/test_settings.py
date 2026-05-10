from __future__ import annotations

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
