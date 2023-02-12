from dataclasses import dataclass

import pytest

from synth.config import Config, Target


@dataclass
class ConfigEquivalenceCase:
    synth: str
    yaml: str
    config: Config


CASES = [
    ConfigEquivalenceCase(
        synth="""\
a:
    echo hi
""",
        yaml="""\
targets:
  - id: a
    commands: echo hi
""",
        config=Config(
            targets=(
                Target(
                    id="a",
                    commands="""\
                    echo hi
                    """,
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
  - id: b
    commands: echo bye
""",
        config=Config(
            targets=(
                Target(
                    id="a",
                    commands="echo a",
                ),
                Target(
                    id="b",
                    commands="echo b",
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
