import shutil
from pathlib import Path

import pytest
from rich.style import Style

from synthesize.config import (
    After,
    AnyTrigger,
    Args,
    Config,
    Flow,
    Node,
    Once,
    Recipe,
    ResolvedFlow,
    ResolvedNode,
    Restart,
    Settings,
    Watch,
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
def test_recipe_commands_dedenting(raw: str, expected: str) -> None:
    assert Recipe(commands=raw).commands == expected


@pytest.mark.parametrize(
    ("recipe", "args", "expected"),
    (
        (
            Recipe(commands="", executable="sh"),
            Args(),
            f"#!{shutil.which('sh')}\n",
        ),
        (
            Recipe(commands="echo 'hello'", executable="sh"),
            Args(),
            f"#!{shutil.which('sh')}\n\necho 'hello'",
        ),
        (
            Recipe(commands="echo '{{foo}}'", executable="sh"),
            Args({"foo": "bar"}),
            f"#!{shutil.which('sh')}\n\necho 'bar'",
        ),
        (  # unused values are ok
            Recipe(commands="echo '{{foo}}'", executable="sh"),
            Args({"foo": "bar", "baz": "qux"}),
            f"#!{shutil.which('sh')}\n\necho 'bar'",
        ),
        (
            Recipe(commands="echo {{foo}} {{baz}}", executable="sh"),
            Args({"foo": "bar", "baz": "qux"}),
            f"#!{shutil.which('sh')}\n\necho bar qux",
        ),
        (
            Recipe(commands="echo", executable="bash"),
            Args(),
            f"#!{shutil.which('bash')}\n\necho",
        ),
        (
            Recipe(commands="{{ 'yes' if choice else 'no' }}", executable="sh"),
            Args({"choice": True}),
            f"#!{shutil.which('sh')}\n\nyes",
        ),
        (
            Recipe(commands="{{ 'yes' if choice else 'no' }}", executable="sh"),
            Args({"choice": False}),
            f"#!{shutil.which('sh')}\n\nno",
        ),
    ),
)
def test_recipe_rendering(recipe: Recipe, args: Args, expected: str) -> None:
    assert recipe.render(args) == expected


def test_rendering_fails_for_bogus_executable() -> None:
    with pytest.raises(Exception):
        Recipe(executable="bogus").render(Args())


color = random_color()


@pytest.mark.parametrize(
    ("unresolved_node", "id", "recipes", "triggers", "expected"),
    (
        (
            Node(
                recipe=Recipe(commands="echo"),
                triggers=(Once(),),
                color=color,
            ),
            "foo",
            {},
            {},
            ResolvedNode(
                id="foo",
                recipe=Recipe(commands="echo"),
                triggers=(Once(),),
                color=color,
            ),
        ),
        (
            Node(
                recipe="t",
                triggers=(Once(),),
                color=color,
            ),
            "foo",
            {"t": Recipe(commands="echo")},
            {},
            ResolvedNode(
                id="foo",
                recipe=Recipe(commands="echo"),
                triggers=(Once(),),
                color=color,
            ),
        ),
        (
            Node(
                recipe=Recipe(commands="echo"),
                triggers=("r",),
                color=color,
            ),
            "foo",
            {},
            {"r": Once()},
            ResolvedNode(
                id="foo",
                recipe=Recipe(commands="echo"),
                triggers=(Once(),),
                color=color,
            ),
        ),
        (
            Node(
                recipe="t",
                triggers=("r",),
                color=color,
            ),
            "foo",
            {"t": Recipe(commands="echo")},
            {"r": Once()},
            ResolvedNode(
                id="foo",
                recipe=Recipe(commands="echo"),
                triggers=(Once(),),
                color=color,
            ),
        ),
    ),
)
def test_resolve_flow_node(
    unresolved_node: Node,
    id: str,
    recipes: dict[str, Recipe],
    triggers: dict[str, AnyTrigger],
    expected: ResolvedNode,
) -> None:
    assert unresolved_node.resolve(id, recipes, triggers) == expected


@pytest.mark.parametrize(
    ("unresolved_flow", "recipes", "triggers", "expected"),
    (
        (
            Flow(
                nodes={
                    "foo": Node(
                        recipe=Recipe(commands="echo"),
                        triggers=(Once(),),
                        color=color,
                    )
                }
            ),
            {},
            {},
            ResolvedFlow(
                nodes={
                    "foo": ResolvedNode(
                        id="foo",
                        recipe=Recipe(commands="echo"),
                        triggers=(Once(),),
                        color=color,
                    )
                }
            ),
        ),
        (
            Flow(
                nodes={
                    "foo": Node(
                        recipe="t",
                        args={"foo": "bar"},
                        envs={"FOO": "BAR"},
                        triggers=("r",),
                        color=color,
                    )
                },
                args={"baz": "qux"},
                envs={"BAZ": "QUX"},
            ),
            {"t": Recipe(commands="echo")},
            {"r": Restart()},
            ResolvedFlow(
                nodes={
                    "foo": ResolvedNode(
                        id="foo",
                        recipe=Recipe(commands="echo"),
                        args={"foo": "bar"},
                        envs={"FOO": "BAR"},
                        triggers=(Restart(),),
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
    recipes: dict[str, Recipe],
    triggers: dict[str, AnyTrigger],
    expected: ResolvedFlow,
) -> None:
    assert unresolved_flow.resolve(recipes, triggers) == expected


@pytest.mark.parametrize(
    ("config", "expected"),
    (
        (
            Config(
                flows={
                    "flow": Flow(
                        nodes={
                            "foo": Node(
                                recipe="t",
                                args={"foo": "bar"},
                                envs={"FOO": "BAR"},
                                triggers=("r",),
                                color=color,
                            )
                        },
                        args={"baz": "qux"},
                        envs={"BAZ": "QUX"},
                    )
                },
                recipes={"t": Recipe(commands="echo")},
                triggers={"r": Restart()},
            ),
            {
                "flow": ResolvedFlow(
                    nodes={
                        "foo": ResolvedNode(
                            id="foo",
                            recipe=Recipe(commands="echo"),
                            args={"foo": "bar"},
                            envs={"FOO": "BAR"},
                            triggers=(Restart(),),
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


watch = Watch(watch=("/path/to/watch",))
after = After(after=("foo",))


@pytest.mark.parametrize(
    ("triggers", "expected"),
    (
        ((Once(),), (Once(),)),
        ((Restart(),), (Once(),)),
        ((watch,), (Once(),)),
        ((Once(), Restart()), (Once(),)),
        ((watch, Restart()), (Once(),)),
        ((Once(), watch), (Once(),)),
        ((Restart(), watch), (Once(),)),
        ((after,), (after,)),
        ((after, Once()), (after, Once())),
        ((after, Once(), watch), (after, Once())),
        ((after, Once(), watch, Restart()), (after, Once())),
    ),
)
def test_resolved_node_once(triggers: tuple[AnyTrigger, ...], expected: tuple[AnyTrigger, ...]) -> None:
    node = ResolvedNode(
        id="foo",
        recipe=Recipe(commands="echo"),
        triggers=triggers,
        color=color,
    )

    assert node.once().triggers == expected


def test_resolved_flow_once() -> None:
    flow = ResolvedFlow(
        nodes={
            "foo": ResolvedNode(
                id="foo",
                recipe=Recipe(commands="echo"),
                triggers=(Restart(),),
                color=color,
            ),
            "bar": ResolvedNode(
                id="bar",
                recipe=Recipe(commands="echo"),
                triggers=(After(after=("foo",)),),
                color=color,
            ),
        }
    )

    once_flow = flow.once()

    assert len(once_flow.nodes) == 2
    assert once_flow.nodes["foo"].triggers == (Once(),)
    assert once_flow.nodes["bar"].triggers == (After(after=("foo",)),)


def test_settings_defaults() -> None:
    s = Settings()
    assert s.timestamps.sub_second_digits == 0
    assert s.timestamps.include_date is False


def test_settings_can_be_overridden_in_config_yaml() -> None:
    config = Config.model_validate_yaml("""
settings:
  timestamps:
    sub_second_digits: 3
    include_date: true
flows: {}
""")
    assert config.settings.timestamps.sub_second_digits == 3
    assert config.settings.timestamps.include_date is True
