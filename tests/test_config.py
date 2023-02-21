from dataclasses import dataclass
from pathlib import Path

import pytest

from synthesize.config import Config, Target


@dataclass
class ConfigEquivalenceCase:
    synth: str
    yaml: str
    config: Config


CASES = [
    ConfigEquivalenceCase(
        synth="""\
a:
    @color red

    echo hi
""",
        yaml="""\
targets:
  - id: a
    commands: echo hi
    color: red
""",
        config=Config(
            targets=(
                Target(
                    id="a",
                    commands="""\
                    echo hi
                    """,
                    color="red",
                ),
            )
        ),
    ),
    ConfigEquivalenceCase(
        synth="""\
a:
    @color red

    echo hi

b:
    @color blue

    echo bye
""",
        yaml="""\
targets:
  - id: a
    commands: echo hi
    color: red
  - id: b
    commands: echo bye
    color: blue
""",
        config=Config(
            targets=(
                Target(
                    id="a",
                    commands="echo hi",
                    color="red",
                ),
                Target(
                    id="b",
                    commands="echo bye",
                    color="blue",
                ),
            )
        ),
    ),
]


@pytest.mark.parametrize("case", CASES)
def test_config_equivalence(case: ConfigEquivalenceCase) -> None:
    from_synth = Config.parse_synth(case.synth)
    from_yaml = Config.parse_yaml(case.yaml)

    assert from_synth == from_yaml == case.config
    # assert from_yaml == case.config


@pytest.mark.parametrize("example", list((Path(__file__).parent.parent / "examples").iterdir()))
def test_config_examples_parse(example: Path) -> None:
    Config.from_file(example)
