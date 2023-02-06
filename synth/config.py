from __future__ import annotations

from colorsys import hsv_to_rgb
from functools import cache
from pathlib import Path
from random import random
from textwrap import dedent
from typing import Literal

from identify.identify import tags_from_path
from lark import Lark
from pydantic import Field, validator
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

    @validator("commands")
    def dedent_commands(cls, commands: str) -> str:
        return dedent(commands)


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
        parsed = parser().parse(text)
        targets = []
        for target in parsed.children:
            id_token, *line_trees = target.children  # type: ignore[union-attr]

            metas = {}
            command_lines = []
            for line_tree in line_trees:
                if line_tree.data == "meta_line":  # type: ignore[union-attr]
                    metas[line_tree.children[0].value] = tuple(  # type: ignore[union-attr]
                        str(child.value) for child in line_tree.children[1:]  # type: ignore[union-attr]
                    )
                if line_tree.data == "command_line":  # type: ignore[union-attr]
                    command_lines.append(line_tree.children[0].value)  # type: ignore[union-attr]

            command = "".join(command_lines).lstrip("\n").rstrip() + "\n\n"

            targets.append(Target(id=id_token.value, commands=command, **metas))  # type: ignore[union-attr]

        return Config(targets=tuple(targets))


@cache
def parser() -> Lark:
    tree_grammar = r"""
    ?start: (_NL* target)*

    target: ID ":" _NL meta_line* command_line+
    ID: /[\w\-]/+

    meta_line: _META_WS "@" META_ATTR (_META_WS META_ARG)* _NL

    _META_WS: /[ \t]+/
    META_ATTR: /\w+/
    META_ARG: /\w+/

    command_line: COMMAND_LINE | BLANK_LINE
    COMMAND_LINE: /[ \t]+[\w ]*\r?\n/
    BLANK_LINE: /\r?\n/

    _NL: /\r?\n/
    """

    return Lark(tree_grammar, parser="lalr")
