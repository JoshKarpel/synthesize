from __future__ import annotations

import ast
import shlex
import shutil
from collections import defaultdict
from collections.abc import Mapping
from colorsys import hsv_to_rgb
from functools import cached_property
from pathlib import Path
from random import random
from textwrap import dedent
from typing import Annotated, Union

from identify.identify import tags_from_path
from jinja2 import Environment
from networkx import DiGraph
from pydantic import Field, field_validator
from rich.color import Color
from typing_extensions import assert_never

from synthesize.model import Model
from synthesize.utils import hash_data

Args = dict[
    Annotated[
        str,
        Field(
            pattern=r"[a-zA-Z]+",
        ),
    ],
    object,
]
Envs = dict[Annotated[str, Field(min_length=1)], str]
ID = Annotated[str, Field(pattern=r"\w+")]


def random_color() -> str:
    triplet = Color.from_rgb(*(x * 255 for x in hsv_to_rgb(random(), 1, 0.7))).triplet

    if triplet is None:  # pragma: unreachable
        raise Exception("Failed to generate random color; please try again.")

    return triplet.hex


template_environment = Environment()


class Target(Model):
    commands: Annotated[str, Field(description="The commands to run for this target.")] = ""
    args: Annotated[
        Args,
        Field(
            description="Template arguments to apply to this target by default.",
        ),
    ] = {}
    envs: Annotated[
        Envs,
        Field(
            description="Environment variables to apply to this target by default.",
        ),
    ] = {}

    executable: Annotated[str, Field(description="The executable to run this target with.")] = "sh -eu"

    @field_validator("commands")
    @classmethod
    def dedent_commands(cls, commands: str) -> str:
        return dedent(commands).strip()

    def render(self, args: Args) -> str:
        exe, *exe_args = shlex.split(self.executable)
        which_exe = shutil.which(exe)
        if which_exe is None:
            raise Exception(f"Failed to find absolute path to executable for {exe}")

        template = template_environment.from_string(
            "\n".join(
                (
                    f"#!{shlex.join((which_exe, *exe_args))}",
                    "",
                    self.commands,
                )
            )
        )

        return template.render(args)


class Once(Model):
    pass


class After(Model):
    after: Annotated[
        tuple[str, ...],
        Field(
            min_length=1,
            description="The IDs of the nodes to wait for.",
        ),
    ]


class Restart(Model):
    delay: Annotated[
        float,
        Field(
            description="The delay before restarting the command after it exits.",
            ge=0,
        ),
    ] = 1


class Watch(Model):
    watch: Annotated[
        tuple[str, ...],
        Field(
            description="The paths to watch for changes. Directories are watched recursively.",
        ),
    ]


AnyTrigger = Union[
    Once,
    After,
    Restart,
    Watch,
]

RepeatingTrigger = Union[
    Restart,
    Watch,
]


class ResolvedNode(Model):
    id: str

    target: Target
    args: Annotated[
        Args,
        Field(
            description="Template arguments to apply to this node.",
        ),
    ] = {}
    envs: Annotated[
        Envs,
        Field(
            description="Environment variables to apply to this node.",
        ),
    ] = {}

    triggers: tuple[AnyTrigger, ...] = (Once(),)

    color: Annotated[str, Field(default_factory=random_color)]

    @cached_property
    def uid(self) -> str:
        return hash_data(self.model_dump_json(exclude={"color"}).encode())

    def once(self) -> ResolvedNode:
        existing_ok_triggers = tuple(t for t in self.triggers if isinstance(t, (Once, After)))
        triggers = existing_ok_triggers or (Once(),)

        return ResolvedNode(
            id=self.id,
            target=self.target,
            args=self.args,
            envs=self.envs,
            triggers=triggers,
            color=self.color,
        )

    def with_args_and_envs(self, args: Args, envs: Envs) -> ResolvedNode:
        return ResolvedNode(
            id=self.id,
            target=self.target,
            args=self.args | args,
            envs=self.envs | envs,
            triggers=self.triggers,
            color=self.color,
        )


class Node(Model):
    target: Annotated[
        Target | ID,
        Field(
            description="The target to run for this node. It may either be the name of a pre-defined target, or a full target definition.",
        ),
    ]
    args: Annotated[
        Args,
        Field(
            description="Template arguments to apply to this node.",
        ),
    ] = {}
    envs: Annotated[
        Envs,
        Field(
            description="Environment variables to apply to this node.",
        ),
    ] = {}

    triggers: Annotated[
        tuple[AnyTrigger | ID, ...],
        Field(
            description="The list of triggers for this node. Each trigger may be the name of a pre-defined trigger, or a full trigger definition.",
        ),
    ] = (Once(),)

    color: Annotated[
        str,
        Field(
            default_factory=random_color,
            description="The color that will be used to help differentiate this node from others.",
        ),
    ]

    def resolve(
        self,
        id: str,
        targets: Mapping[str, Target],
        triggers: Mapping[str, AnyTrigger],
    ) -> ResolvedNode:
        return ResolvedNode(
            id=id,
            target=targets[self.target] if isinstance(self.target, str) else self.target,
            args=self.args,
            envs=self.envs,
            triggers=tuple(triggers[t] if isinstance(t, str) else t for t in self.triggers),
            color=self.color,
        )


class ResolvedFlow(Model):
    nodes: dict[ID, ResolvedNode]
    args: Annotated[
        Args,
        Field(
            description="Template arguments to apply to all nodes in this flow.",
        ),
    ] = {}
    envs: Annotated[
        Envs,
        Field(
            description="Environment variables to apply to all nodes in this flow.",
        ),
    ] = {}

    def once(self) -> ResolvedFlow:
        return ResolvedFlow(
            nodes={id: node.once() for id, node in self.nodes.items()},
            args=self.args,
            envs=self.envs,
        )

    def with_args_and_envs_from_cli(self, args: list[str], envs: list[str]) -> ResolvedFlow:
        new_node_args = defaultdict(dict)
        new_node_envs = defaultdict(dict)
        new_args = {}
        new_envs = {}
        for a in args:
            if "=" not in a:  # TODO bad, use a regex
                raise ValueError(f"Invalid argument '{a}'; must be in the form 'key=value'")
            key, val = a.split("=", 1)
            val = eval_cli_arg(val)
            if "." in key:  # TODO bad, use a regex
                node, key = key.split(".", 1)
                if node not in self.nodes:
                    raise ValueError(f"Invalid argument '{a}'; no such node '{node}'")

                new_node_args[node][key] = val
            else:
                new_args[key] = val
        for e in envs:
            if "=" not in e:  # TODO bad, use a regex
                raise ValueError(f"Invalid environment variable '{e}'; must be in the form 'key=value'")
            key, val = e.split("=", 1)
            if "." in key:  # TODO bad, use a regex
                node, key = key.split(".", 1)
                if node not in self.nodes:
                    raise ValueError(f"Invalid environment variable '{e}'; no such node '{node}'")

                new_node_envs[node][key] = val
            else:
                new_envs[key] = val

        return ResolvedFlow(
            nodes={
                id: node.with_args_and_envs(args=new_node_args[id], envs=new_node_envs[id])
                for id, node in self.nodes.items()
            },
            args=self.args | new_args,
            envs=self.envs | new_envs,
        )

    @cached_property
    def graph(self) -> DiGraph:
        graph = DiGraph()

        for id, node in self.nodes.items():
            graph.add_node(id)
            for t in node.triggers:
                if isinstance(t, After):
                    for predecessor_id in t.after:
                        graph.add_edge(predecessor_id, id)

        return graph

    def mermaid(self) -> str:
        lines = ["flowchart TD"]

        seen_watches = set()
        for id, node in self.nodes.items():
            lines.append(f"{node.id}({id})")

            for t in node.triggers:
                match t:
                    case Once():
                        pass
                    case After(after=after):
                        for a in after:
                            lines.append(f"{self.nodes[a].id} --> {node.id}")
                    case Restart(delay=delay):
                        lines.append(f"{node.id} -->|∞ {delay:.3g}s| {node.id}")
                    case Watch(watch=paths):
                        text = "\n".join(paths)
                        h = hash_data("".join(paths))
                        if h not in seen_watches:
                            seen_watches.add(h)
                            lines.append(f'w_{h}[("{text}")]')
                        lines.append(f"w_{h} -->|👁| {node.id}")
                    case never:
                        assert_never(never)

        return "\n  ".join(lines).strip()


def eval_cli_arg(arg: str) -> object:
    try:
        node = ast.parse(arg)
    except SyntaxError:
        return arg
    if isinstance(node, ast.Constant):
        return ast.literal_eval(node)
    else:
        return arg


class Flow(Model):
    nodes: Annotated[
        Mapping[ID, Node],
        Field(
            description="Mapping of IDs to nodes.",
        ),
    ] = {}
    args: Annotated[
        Args,
        Field(
            description="Template arguments to apply to all nodes in this flow.",
        ),
    ] = {}
    envs: Annotated[
        Envs,
        Field(
            description="Environment variables to apply to all nodes in this flow.",
        ),
    ] = {}

    def resolve(
        self,
        targets: Mapping[ID, Target],
        triggers: Mapping[ID, AnyTrigger],
    ) -> ResolvedFlow:
        return ResolvedFlow(
            nodes={id: node.resolve(id, targets, triggers) for id, node in self.nodes.items()},
            args=self.args,
            envs=self.envs,
        )


class Config(Model):
    flows: Annotated[
        Mapping[ID, Flow],
        Field(
            description="A mapping of IDs to flows.",
        ),
    ] = {}
    targets: Annotated[
        Mapping[ID, Target],
        Field(
            description="A mapping of IDs to targets.",
        ),
    ] = {}
    triggers: Annotated[
        Mapping[ID, AnyTrigger],
        Field(
            description="A mapping of IDs to triggers.",
        ),
    ] = {}

    @classmethod
    def from_file(cls, file: Path) -> Config:
        tags = tags_from_path(str(file))

        if "yaml" in tags:
            return cls.model_validate_yaml(file.read_text())
        else:
            raise NotImplementedError("Currently, only YAML files are supported.")

    def resolve(self) -> Mapping[ID, ResolvedFlow]:
        return {id: flow.resolve(self.targets, self.triggers) for id, flow in self.flows.items()}
