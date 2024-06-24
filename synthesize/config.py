from __future__ import annotations

from colorsys import hsv_to_rgb
from pathlib import Path
from random import random
from textwrap import dedent
from typing import Annotated, Literal, Union

from identify.identify import tags_from_path
from pydantic import Field, field_validator
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

    @field_validator("commands")
    @classmethod
    def dedent_commands(cls, commands: str) -> str:
        return dedent(commands).strip()


class Once(Model):
    type: Literal["once"] = "once"


class After(Model):
    type: Literal["after"] = "after"

    after: frozenset[str] = Field(default=...)


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
    trigger: AnyTrigger

    color: str


class TargetRef(Model):
    id: str


class TriggerRef(Model):
    id: str


class UnresolvedFlowNode(Model):
    id: str

    target: Target | TargetRef
    trigger: AnyTrigger | TriggerRef = Once()

    color: Annotated[str, Field(default_factory=random_color)]

    def resolve(
        self,
        targets: dict[str, Target],
        triggers: dict[str, AnyTrigger],
    ) -> FlowNode:
        return FlowNode(
            id=self.id,
            target=targets[self.target.id] if isinstance(self.target, TargetRef) else self.target,
            trigger=(
                triggers[self.trigger.id] if isinstance(self.trigger, TriggerRef) else self.trigger
            ),
            color=self.color,
        )


class Flow(Model):
    nodes: tuple[FlowNode, ...]


class UnresolvedFlow(Model):
    nodes: tuple[UnresolvedFlowNode, ...]

    def resolve(self, targets: dict[str, Target], triggers: dict[str, AnyTrigger]) -> Flow:
        return Flow(nodes=tuple(node.resolve(targets, triggers) for node in self.nodes))


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

    def resolve(self) -> dict[str, Flow]:
        return {id: flow.resolve(self.targets, self.triggers) for id, flow in self.flows.items()}
