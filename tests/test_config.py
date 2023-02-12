from dataclasses import dataclass

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
    echo hi

b:
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
    # from_synth = Config.parse_synth(case.synthesize)
    from_yaml = Config.parse_yaml(case.yaml)

    # assert from_synth == from_yaml == case.config
    assert from_yaml == case.config
