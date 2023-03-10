from __future__ import annotations

from collections import ChainMap
from colorsys import hsv_to_rgb
from pathlib import Path
from random import random
from textwrap import dedent
from typing import Generator, Literal

from identify.identify import tags_from_path
from parsy import Parser, generate, regex, string
from pydantic import Field, validator
from rich.color import Color

from synthesize.model import Model


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

    if triplet is None:  # pragma: unreachable
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

    @validator("commands")
    def dedent_commands(cls, commands: str) -> str:
        return dedent(commands).strip()


class Config(Model):
    targets: tuple[Target, ...]

    @classmethod
    def from_file(cls, file: Path) -> Config:
        tags = tags_from_path(str(file))

        if "yaml" in tags:
            return cls.parse_yaml(file.read_text())
        else:
            return cls.parse_synth(file.read_text())

    @classmethod
    def parse_synth(cls, text: str) -> Config:
        parsed = config.parse(text)
        return cls.parse_obj(parsed)


ConfigFragment = dict[str, object]
ConfigFragmentGenerator = Generator[Parser, None, ConfigFragment]


@generate
def config() -> ConfigFragmentGenerator:
    targets = yield target.many()

    return {"targets": targets}


@generate
def target() -> ConfigFragmentGenerator:
    id = yield target_id << string(":") << eol

    metas: list[ConfigFragment] | None = yield meta.many()
    m = dict(ChainMap(*(metas or [])))

    command_lines: list[str] | None = yield command_line.many()

    return {"id": id, "commands": "".join(command_lines or []), **m}


@generate
def after() -> ConfigFragmentGenerator:
    yield indent >> string("@after") >> padding

    ids = yield target_id.sep_by(padding, min=1) << eol

    return {"after": ids}


@generate
def once() -> ConfigFragmentGenerator:
    type = yield indent >> string("@") >> string("once") << eol

    return {"lifecycle": {"type": type}}


@generate
def restart() -> ConfigFragmentGenerator:
    type = yield indent >> meta_marker >> string("restart") << eol.optional()

    delay = yield (padding >> number << eol).optional()
    d: ConfigFragment = {"delay": delay} if delay else {}

    return {"lifecycle": {"type": type, **d}}  # type: ignore[arg-type]


@generate
def watch() -> ConfigFragmentGenerator:
    type = yield indent >> meta_marker >> string("watch") << padding

    paths = yield path.sep_by(padding, min=1) << eol

    return {"lifecycle": {"type": type, "paths": paths}}


@generate
def color() -> ConfigFragmentGenerator:
    color = yield indent >> meta_marker >> string("color") >> padding >> regex(r".+") << eol

    return {"color": color}


number = regex(r"([0-9]*[.])?[0-9]+")
padding = regex(r"[ \t]+")
target_id = regex(r"[\w\-]+")
path = regex(r"[\w\/]*")
indent = regex(r"[ \t]+")
eol = regex(r"\s*\r?\n")
command = regex(r".*\r?\n")
command_line = (indent >> command) | eol
meta_marker = string("@")
lifecycle = once | restart | watch
meta = after | lifecycle | color
