from __future__ import annotations

from datetime import datetime
from functools import cached_property
from types import TracebackType
from typing import Type

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.rule import Rule
from rich.style import Style
from rich.table import Table
from rich.text import Text
from watchfiles import Change

from synthesize.messages import (
    CommandLifecycleEvent,
    CommandMessage,
    Message,
    TargetExited,
    TargetStarted,
    WatchPathChanged,
)
from synthesize.state import State

prefix_format = "{timestamp:%H:%M:%S} {id}  "
internal_format = "{timestamp:%H:%M:%S}"
CHANGE_TO_STYLE = {
    Change.added: Style(color="green"),
    Change.deleted: Style(color="red"),
    Change.modified: Style(color="yellow"),
}


class Renderer:
    def __init__(self, state: State, console: Console):
        self.state = state
        self.console = console

        self.live = Live(console=console, auto_refresh=False)

    def __enter__(self) -> None:
        self.live.start(refresh=True)

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.live.stop()

    def handle_message(self, message: Message) -> None:
        match message:
            case CommandMessage() as msg:
                self.handle_command_message(msg)

            case TargetStarted() as msg:
                self.handle_lifecycle_message(msg)

            case TargetExited() as msg:
                self.handle_lifecycle_message(msg)

            case WatchPathChanged() as msg:
                self.handle_lifecycle_message(msg)

        self.update(message)

    def info(self, event: Message) -> RenderableType:
        table = Table.grid(padding=(1, 1, 0, 0))

        running_targets = self.state.running_targets()

        running = (
            Text.assemble(
                "Running ",
                Text(" ").join(
                    Text(t.id, style=Style(color="black", bgcolor=t.color))
                    for t in sorted(running_targets, key=lambda t: t.id)
                ),
            )
            if running_targets
            else Text()
        )

        table.add_row(
            internal_format.format_map({"timestamp": event.timestamp}),
            running,
        )

        return Group(Rule(style=(Style(color="green" if running_targets else "yellow"))), table)

    def render_prefix(
        self, message: CommandMessage | CommandLifecycleEvent | WatchPathChanged
    ) -> str:
        return prefix_format.format_map(
            {"id": message.target.id, "timestamp": message.timestamp}
        ).ljust(self.prefix_width)

    def handle_command_message(self, message: CommandMessage) -> None:
        prefix = Text(
            self.render_prefix(message),
            style=Style(color=message.target.color),
        )

        body = Text.from_ansi(message.text)

        g = Table.grid()
        g.add_row(prefix, body)

        self.console.print(g)

    def handle_lifecycle_message(self, message: CommandLifecycleEvent | WatchPathChanged) -> None:
        prefix = Text.from_markup(
            self.render_prefix(message),
            style=Style(color=message.target.color),
        )

        parts: tuple[str | tuple[str, str] | tuple[str, Style] | Text, ...]

        match message:
            case TargetStarted(target=target, pid=pid):
                parts = (
                    "Target ",
                    (target.id, target.color),
                    f" started (pid {pid})",
                )
            case TargetExited(target=target, pid=pid, exit_code=exit_code):
                parts = (
                    "Target ",
                    (target.id, target.color),
                    f" (pid {pid}) exited with code ",
                    (str(exit_code), "green" if exit_code == 0 else "red"),
                )
            case WatchPathChanged(target=target):
                changes = Text(" ").join(
                    Text(path, style=CHANGE_TO_STYLE[change]) for change, path in message.changes
                )

                parts = (
                    "Running target ",
                    (target.id, target.color),
                    " due to detected changes: ",
                    changes,
                )

        body = Text.assemble(
            *parts,
            style=Style(dim=True),
        )

        g = Table.grid()
        g.add_row(prefix, body)

        self.console.print(g)

    def handle_shutdown_start(self) -> None:
        self.live.update(Group(Rule(), Text("Shutting down...")), refresh=True)

    def handle_shutdown_end(self) -> None:
        self.live.update(Rule(), refresh=True)

    def update(self, message: Message) -> None:
        self.live.update(self.info(message), refresh=True)

    @cached_property
    def prefix_width(self) -> int:
        now = datetime.now()

        return len(
            max(
                (
                    prefix_format.format_map({"timestamp": now, "id": t.id})
                    for t in self.state.targets()
                ),
                key=len,
            )
        )
