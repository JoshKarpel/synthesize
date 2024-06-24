from pathlib import Path

import pytest
from rich.style import Style

from synthesize.config import Config, random_color


@pytest.mark.parametrize("example", list((Path(__file__).parent.parent / "examples").iterdir()))
def test_config_examples_parse(example: Path) -> None:
    Config.from_file(example)


def test_can_make_style_from_random_color() -> None:
    assert Style(color=random_color())
