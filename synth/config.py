from __future__ import annotations

import random
from pathlib import Path
from typing import Literal

from pydantic import Field

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

    paths: tuple[Path, ...] = Field(...)


def random_style() -> str:
    return f"#{''.join(random.choices('ABCDEF', k=6))}"


class Command(Model):
    pass


class ShellCommand(Command):
    type: Literal["shell"] = "shell"

    args: str


class Target(Model):
    id: str

    commands: tuple[ShellCommand] = Field(default=())
    shutdown: tuple[ShellCommand] = Field(default=())

    after: tuple[str, ...] = Field(default=())
    lifecycle: Once | Restart | Watch = Once()

    style: str = Field(default_factory=random_style)


class Config(Model):
    targets: tuple[Target, ...]
