from __future__ import annotations

from colorsys import hsv_to_rgb
from pathlib import Path
from random import random
from textwrap import dedent
from typing import Annotated, Literal, Union

from identify.identify import tags_from_path
from pydantic import Field, validator
from rich.color import Color

from synthesize.model import Model


def random_color() -> str:
    triplet = Color.from_rgb(*(x * 255 for x in hsv_to_rgb(random(), 1, 0.7))).triplet

    if triplet is None:  # pragma: unreachable
        raise Exception("Failed to generate random color; please try again.")

    return triplet.hex


class Target(Model):
    commands: str = Field(default="")
    executable: str = Field(default="sh -u")

    @validator("commands")
    def dedent_commands(cls, commands: str) -> str:
        return dedent(commands).strip()


class Once(Model):
    type: Literal["once"] = "once"


class After(Model):
    type: Literal["after"] = "after"

    after: tuple[str, ...] = Field(default=...)


class Restart(Model):
    type: Literal["restart"] = "restart"

    delay: float = Field(
        default=1, description="The delay before restarting the command after it exits.", ge=0
    )


class Watch(Model):
    type: Literal["watch"] = "watch"

    paths: tuple[str, ...]


AnyTrigger = Union[
    Once,
    After,
    Restart,
    Watch,
]


class TargetRef(Model):
    id: str

    args: Annotated[dict[str, str], Field(default_factory=dict)]


class TriggerRef(Model):
    id: str


class UnresolvedFlowNode(Model):
    id: str

    target: Target | TargetRef
    trigger: AnyTrigger | TriggerRef = Once()

    color: Annotated[str, Field(default_factory=random_color)]


class UnresolvedFlow(Model):
    nodes: tuple[UnresolvedFlowNode, ...]


class Config(Model):
    targets: Annotated[dict[str, Target], Field(default_factory=dict)]
    triggers: Annotated[dict[str, AnyTrigger], Field(default_factory=dict)]
    flows: Annotated[dict[str, UnresolvedFlow], Field(default_factory=dict)]

    @classmethod
    def from_file(cls, file: Path) -> Config:
        tags = tags_from_path(str(file))

        if "yaml" in tags:
            return cls.parse_yaml(file.read_text())
        else:
            raise NotImplementedError("Currently, only YAML files are supported.")
