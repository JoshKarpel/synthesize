from __future__ import annotations

from colorsys import hsv_to_rgb
from random import random
from typing import Literal

from pydantic import Field
from rich.color import Color

from synth.model import Model


class Lifecycle(Model):
    pass


class Once(Lifecycle):
    type: Literal["once"] = "once"


class Restart(Lifecycle):
    type: Literal["restart"] = "restart"

    delay: float = Field(
        default=1, description="The delay before restarting the command after it exits.", ge=0
    )


class Watch(Lifecycle):
    type: Literal["watch"] = "watch"

    paths: tuple[str, ...] = Field(...)


def random_color() -> str:
    triplet = Color.from_rgb(*(x * 255 for x in hsv_to_rgb(random(), 1, 0.7))).triplet

    if triplet is None:
        raise Exception("Failed to generate random color; please try again.")

    return triplet.hex


class Command(Model):
    pass


class ShellCommand(Command):
    type: Literal["shell"] = "shell"

    args: str


class Target(Model):
    id: str

    commands: str = Field(default="")
    executable: str = Field(default="sh -u")

    after: tuple[str, ...] = Field(default=())
    lifecycle: Once | Restart | Watch = Once()

    color: str = Field(default_factory=random_color)


class Config(Model):
    targets: tuple[Target, ...]
