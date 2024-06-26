from __future__ import annotations

import shlex
import shutil
from colorsys import hsv_to_rgb
from pathlib import Path
from random import random
from stat import S_IEXEC
from textwrap import dedent
from typing import Annotated, Literal, Union

from frozendict import frozendict
from identify.identify import tags_from_path
from jinja2 import Environment
from pydantic import Field, field_validator
from rich.color import Color

from synthesize.model import Model
from synthesize.utils import FrozenDict, md5

ArgValue = int | float | str | bool | None

Args = Annotated[
    FrozenDict[
        Annotated[
            str,
            Field(
                # https://jinja.palletsprojects.com/en/3.1.x/api/#notes-on-identifiers
                pattern=r"[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*",
                min_length=1,
            ),
        ],
        ArgValue,
    ],
    Field(default_factory=frozendict),
]
Envs = Annotated[
    FrozenDict[
        Annotated[
            str,
            Field(
                min_length=1,
            ),
        ],
        str,
    ],
    Field(default_factory=frozendict),
]


def random_color() -> str:
    triplet = Color.from_rgb(*(x * 255 for x in hsv_to_rgb(random(), 1, 0.7))).triplet

    if triplet is None:  # pragma: unreachable
        raise Exception("Failed to generate random color; please try again.")

    return triplet.hex


template_environment = Environment()


class Target(Model):
    commands: str = Field(default="")
    executable: str = Field(default="sh -u")

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

    after: Annotated[frozenset[str], Field(min_length=1)]


class Restart(Model):
    type: Literal["restart"] = "restart"

    delay: Annotated[
        float,
        Field(
            default=1,
            description="The delay before restarting the command after it exits.",
            ge=0,
        ),
    ]


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
    args: Args
    envs: Envs

    trigger: AnyTrigger

    color: str

    def write_script(self, tmp_dir: Path, flow_args: Args) -> Path:
        path = tmp_dir / f"{self.id}-{md5(self.model_dump_json().encode())}"

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self.target.render(
                args=flow_args
                | self.args
                | {
                    "id": self.id,
                }
            )
        )
        path.chmod(path.stat().st_mode | S_IEXEC)

        return path


class UnresolvedFlowNode(Model):
    target: Target | str
    args: Args
    envs: Envs

    trigger: AnyTrigger | str = Once()

    color: Annotated[str, Field(default_factory=random_color)]

    def resolve(
        self,
        id: str,
        targets: dict[str, Target],
        triggers: dict[str, AnyTrigger],
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
    nodes: dict[str, FlowNode]
    args: Args = Field(default_factory=frozendict)
    envs: Envs = Field(default_factory=frozendict)


class UnresolvedFlow(Model):
    nodes: dict[str, UnresolvedFlowNode]
    args: Args = Field(default_factory=frozendict)
    envs: Envs = Field(default_factory=frozendict)

    def resolve(
        self,
        targets: dict[str, Target],
        triggers: dict[str, AnyTrigger],
    ) -> Flow:
        return Flow(
            nodes={
                node_id: node.resolve(node_id, targets, triggers)
                for node_id, node in self.nodes.items()
            },
            args=self.args,
            envs=self.envs,
        )


class Config(Model):
    targets: Annotated[dict[str, Target], Field(default_factory=dict)]
    triggers: Annotated[dict[str, AnyTrigger], Field(default_factory=dict)]
    flows: Annotated[dict[str, UnresolvedFlow], Field(default_factory=dict)]

    @classmethod
    def from_file(cls, file: Path) -> Config:
        tags = tags_from_path(str(file))

        if "yaml" in tags:
            return cls.model_validate_yaml(file.read_text())
        else:
            raise NotImplementedError("Currently, only YAML files are supported.")

    def resolve(self) -> dict[str, Flow]:
        return {
            flow_id: flow.resolve(self.targets, self.triggers)
            for flow_id, flow in self.flows.items()
        }
