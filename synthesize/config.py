from __future__ import annotations

import shlex
import shutil
from collections.abc import Mapping
from colorsys import hsv_to_rgb
from functools import cached_property
from pathlib import Path
from random import random
from textwrap import dedent
from typing import Annotated, Literal, Union

from identify.identify import tags_from_path
from jinja2 import Environment
from pydantic import Field, field_validator
from rich.color import Color
from typing_extensions import assert_never

from synthesize.model import Model
from synthesize.utils import md5

Args = dict[
    Annotated[
        str,
        Field(
            # https://jinja.palletsprojects.com/en/3.1.x/api/#notes-on-identifiers
            pattern=r"[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*",
            min_length=1,
        ),
    ],
    object,
]
Envs = dict[
    Annotated[
        str,
        Field(
            min_length=1,
        ),
    ],
    str,
]
ID = Annotated[
    str,
    Field(
        pattern=r"\w+",
    ),
]


def random_color() -> str:
    triplet = Color.from_rgb(*(x * 255 for x in hsv_to_rgb(random(), 1, 0.7))).triplet

    if triplet is None:  # pragma: unreachable
        raise Exception("Failed to generate random color; please try again.")

    return triplet.hex


template_environment = Environment()


class Target(Model):
    commands: str = ""
    args: Args = {}
    envs: Envs = {}

    executable: str = "sh -eu"

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
    type: Literal["once"] = "once"


class After(Model):
    type: Literal["after"] = "after"

    after: Annotated[tuple[str, ...], Field(min_length=1)]


class Restart(Model):
    type: Literal["restart"] = "restart"

    delay: Annotated[
        float,
        Field(
            description="The delay before restarting the command after it exits.",
            ge=0,
        ),
    ] = 1


class Watch(Model):
    type: Literal["watch"] = "watch"

    paths: tuple[str, ...]


AnyTrigger = Union[
    Once,
    After,
    Restart,
    Watch,
]


class FlowNode(Model):
    id: str

    target: Target
    args: Args = {}
    envs: Envs = {}

    trigger: AnyTrigger = Once()

    color: Annotated[str, Field(default_factory=random_color)]

    @cached_property
    def uid(self) -> str:
        return md5(self.model_dump_json(exclude={"color"}).encode())


class UnresolvedFlowNode(Model):
    target: Target | ID
    args: Args = {}
    envs: Envs = {}

    trigger: AnyTrigger | ID = Once()

    color: Annotated[str, Field(default_factory=random_color)]

    def resolve(
        self,
        id: str,
        targets: Mapping[str, Target],
        triggers: Mapping[str, AnyTrigger],
    ) -> FlowNode:
        return FlowNode(
            id=id,
            target=targets[self.target] if isinstance(self.target, str) else self.target,
            args=self.args,
            envs=self.envs,
            trigger=(triggers[self.trigger] if isinstance(self.trigger, str) else self.trigger),
            color=self.color,
        )


class Flow(Model):
    nodes: dict[ID, FlowNode]
    args: Args = {}
    envs: Envs = {}

    def mermaid(self) -> str:
        lines = ["flowchart TD"]

        seen_watches = set()
        for id, node in self.nodes.items():
            lines.append(f"{node.id}({id})")

            match node.trigger:
                case Once():
                    pass
                case After(after=after):
                    for a in after:
                        lines.append(f"{self.nodes[a].id} --> {node.id}")
                case Restart(delay=delay):
                    lines.append(f"{node.id} -->|∞ {delay:.3g}s| {node.id}")
                case Watch(paths=paths):
                    text = "\n".join(paths)
                    h = md5("".join(paths))
                    if h not in seen_watches:
                        seen_watches.add(h)
                        lines.append(f'w_{h}[("{text}")]')
                    lines.append(f"w_{h} -->|👁| {node.id}")
                case never:
                    assert_never(never)

        return "\n  ".join(lines).strip()


class UnresolvedFlow(Model):
    nodes: dict[ID, UnresolvedFlowNode]
    args: Args = {}
    envs: Envs = {}

    def resolve(
        self,
        targets: Mapping[ID, Target],
        triggers: Mapping[ID, AnyTrigger],
    ) -> Flow:
        return Flow(
            nodes={id: node.resolve(id, targets, triggers) for id, node in self.nodes.items()},
            args=self.args,
            envs=self.envs,
        )


class Config(Model):
    flows: dict[ID, UnresolvedFlow] = {}
    targets: dict[ID, Target] = {}
    triggers: dict[ID, AnyTrigger] = {}

    @classmethod
    def from_file(cls, file: Path) -> Config:
        tags = tags_from_path(str(file))

        if "yaml" in tags:
            return cls.model_validate_yaml(file.read_text())
        else:
            raise NotImplementedError("Currently, only YAML files are supported.")

    def resolve(self) -> Mapping[ID, Flow]:
        return {id: flow.resolve(self.targets, self.triggers) for id, flow in self.flows.items()}
