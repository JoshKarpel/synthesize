import shutil
from pathlib import Path

import pytest
from rich.style import Style

from synthesize.config import (
    AnyTrigger,
    Args,
    Config,
    Flow,
    FlowNode,
    Once,
    ResolvedFlow,
    ResolvedFlowNode,
    Restart,
    Target,
    random_color,
)

ROOT = Path(__file__).parent.parent
EXAMPLES = [
    *(ROOT / "docs" / "examples").iterdir(),
    ROOT / "synth.yaml",
]


@pytest.mark.parametrize("example", EXAMPLES)
def test_can_generate_mermaid_from_examples(example: Path) -> None:
    for flow in Config.from_file(example).resolve().values():
        flow.mermaid()


def test_can_make_style_from_random_color() -> None:
    assert Style(color=random_color())


@pytest.mark.parametrize(
    ("raw", "expected"),
    (
        ("echo 'hello'", "echo 'hello'"),
        ("  echo 'hello'", "echo 'hello'"),
        (" echo ", "echo"),
        (
            """
            echo
            """,
            "echo",
        ),
        (
            """
            echo
            echo
            """,
            "echo\necho",
        ),
    ),
)
def test_target_commands_dedenting(raw: str, expected: str) -> None:
    assert Target(commands=raw).commands == expected


@pytest.mark.parametrize(
    ("target", "args", "expected"),
    (
        (
            Target(commands="", executable="sh"),
            Args(),
            f"#!{shutil.which('sh')}\n",
        ),
        (
            Target(commands="echo 'hello'", executable="sh"),
            Args(),
            f"#!{shutil.which('sh')}\n\necho 'hello'",
        ),
        (
            Target(commands="echo '{{foo}}'", executable="sh"),
            Args({"foo": "bar"}),
            f"#!{shutil.which('sh')}\n\necho 'bar'",
        ),
        (  # unused values are ok
            Target(commands="echo '{{foo}}'", executable="sh"),
            Args({"foo": "bar", "baz": "qux"}),
            f"#!{shutil.which('sh')}\n\necho 'bar'",
        ),
        (
            Target(commands="echo {{foo}} {{baz}}", executable="sh"),
            Args({"foo": "bar", "baz": "qux"}),
            f"#!{shutil.which('sh')}\n\necho bar qux",
        ),
        (
            Target(commands="echo", executable="bash"),
            Args(),
            f"#!{shutil.which('bash')}\n\necho",
        ),
        (
            Target(commands="{{ 'yes' if choice else 'no' }}", executable="sh"),
            Args({"choice": True}),
            f"#!{shutil.which('sh')}\n\nyes",
        ),
        (
            Target(commands="{{ 'yes' if choice else 'no' }}", executable="sh"),
            Args({"choice": False}),
            f"#!{shutil.which('sh')}\n\nno",
        ),
    ),
)
def test_target_rendering(target: Target, args: Args, expected: str) -> None:
    assert target.render(args) == expected


def test_rendering_fails_for_bogus_executable() -> None:
    with pytest.raises(Exception):
        Target(executable="bogus").render(Args())


color = random_color()


@pytest.mark.parametrize(
    ("unresolved_node", "id", "targets", "triggers", "expected"),
    (
        (
            FlowNode(
                target=Target(commands="echo"),
                triggers=[Once()],
                color=color,
            ),
            "foo",
            {},
            {},
            ResolvedFlowNode(
                id="foo",
                target=Target(commands="echo"),
                triggers=[Once()],
                color=color,
            ),
        ),
        (
            FlowNode(
                target="t",
                triggers=[Once()],
                color=color,
            ),
            "foo",
            {"t": Target(commands="echo")},
            {},
            ResolvedFlowNode(
                id="foo",
                target=Target(commands="echo"),
                triggers=[Once()],
                color=color,
            ),
        ),
        (
            FlowNode(
                target=Target(commands="echo"),
                triggers=["r"],
                color=color,
            ),
            "foo",
            {},
            {"r": Once()},
            ResolvedFlowNode(
                id="foo",
                target=Target(commands="echo"),
                triggers=[Once()],
                color=color,
            ),
        ),
        (
            FlowNode(
                target="t",
                triggers=["r"],
                color=color,
            ),
            "foo",
            {"t": Target(commands="echo")},
            {"r": Once()},
            ResolvedFlowNode(
                id="foo",
                target=Target(commands="echo"),
                triggers=[Once()],
                color=color,
            ),
        ),
    ),
)
def test_resolve_flow_node(
    unresolved_node: FlowNode,
    id: str,
    targets: dict[str, Target],
    triggers: dict[str, AnyTrigger],
    expected: ResolvedFlowNode,
) -> None:
    assert unresolved_node.resolve(id, targets, triggers) == expected


@pytest.mark.parametrize(
    ("unresolved_flow", "targets", "triggers", "expected"),
    (
        (
            Flow(
                nodes={
                    "foo": FlowNode(
                        target=Target(commands="echo"),
                        triggers=[Once()],
                        color=color,
                    )
                }
            ),
            {},
            {},
            ResolvedFlow(
                nodes={
                    "foo": ResolvedFlowNode(
                        id="foo",
                        target=Target(commands="echo"),
                        triggers=[Once()],
                        color=color,
                    )
                }
            ),
        ),
        (
            Flow(
                nodes={
                    "foo": FlowNode(
                        target="t",
                        args={"foo": "bar"},
                        envs={"FOO": "BAR"},
                        triggers=["r"],
                        color=color,
                    )
                },
                args={"baz": "qux"},
                envs={"BAZ": "QUX"},
            ),
            {"t": Target(commands="echo")},
            {"r": Restart()},
            ResolvedFlow(
                nodes={
                    "foo": ResolvedFlowNode(
                        id="foo",
                        target=Target(commands="echo"),
                        args={"foo": "bar"},
                        envs={"FOO": "BAR"},
                        triggers=[Restart()],
                        color=color,
                    )
                },
                args={"baz": "qux"},
                envs={"BAZ": "QUX"},
            ),
        ),
    ),
)
def test_resolve_flow(
    unresolved_flow: Flow,
    targets: dict[str, Target],
    triggers: dict[str, AnyTrigger],
    expected: ResolvedFlow,
) -> None:
    assert unresolved_flow.resolve(targets, triggers) == expected


@pytest.mark.parametrize(
    ("config", "expected"),
    (
        (
            Config(
                flows={
                    "flow": Flow(
                        nodes={
                            "foo": FlowNode(
                                target="t",
                                args={"foo": "bar"},
                                envs={"FOO": "BAR"},
                                triggers=["r"],
                                color=color,
                            )
                        },
                        args={"baz": "qux"},
                        envs={"BAZ": "QUX"},
                    )
                },
                targets={"t": Target(commands="echo")},
                triggers={"r": Restart()},
            ),
            {
                "flow": ResolvedFlow(
                    nodes={
                        "foo": ResolvedFlowNode(
                            id="foo",
                            target=Target(commands="echo"),
                            args={"foo": "bar"},
                            envs={"FOO": "BAR"},
                            triggers=[Restart()],
                            color=color,
                        )
                    },
                    args={"baz": "qux"},
                    envs={"BAZ": "QUX"},
                ),
            },
        ),
    ),
)
def test_resolve_config(
    config: Config,
    expected: dict[str, ResolvedFlow],
) -> None:
    assert config.resolve() == expected
