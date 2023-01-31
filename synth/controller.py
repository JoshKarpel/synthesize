from __future__ import annotations

from asyncio import Task, create_task, sleep, wait
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import cached_property
from pathlib import Path

from networkx import DiGraph
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.rule import Rule
from rich.style import Style
from rich.table import Table
from rich.text import Text
from watchfiles import Change, awatch

from synth.config import Config, Restart, Target, Watch
from synth.events import (
    CommandExited,
    CommandLifecycleEvent,
    CommandMessage,
    CommandStarted,
    Event,
    Heartbeat,
    WatchPathChanged,
)
from synth.execution import Execution
from synth.fanout import Fanout
from synth.utils import delay


class TargetStatus(Enum):
    Pending = "pending"
    Running = "running"
    Done = "done"


@dataclass(frozen=True)
class State:
    graph: DiGraph
    id_to_target: dict[str, Target]
    id_to_status: dict[str, TargetStatus]

    @classmethod
    def from_targets(cls, targets: Iterable[Target]) -> State:
        id_to_target = {target.id: target for target in targets}

        graph = DiGraph()

        for id, target in id_to_target.items():
            graph.add_node(target.id)
            for predecessor_id in target.after:
                graph.add_edge(predecessor_id, id)

        return State(
            graph=graph,
            id_to_target=id_to_target,
            id_to_status={id: TargetStatus.Pending for id in id_to_target.keys()},
        )

    def running_targets(self) -> set[Target]:
        return {
            self.id_to_target[id]
            for id, status in self.id_to_status.items()
            if status is TargetStatus.Running
        }

    def ready_targets(self) -> set[Target]:
        pending_target_ids = {
            id for id, status in self.id_to_status.items() if status is TargetStatus.Pending
        }

        pending_subgraph: DiGraph = self.graph.subgraph(pending_target_ids)

        return {
            self.id_to_target[id]
            for id in pending_subgraph.nodes
            if not any(pending_subgraph.predecessors(id))
        }

    def mark_done(self, target: Target) -> None:
        self.id_to_status[target.id] = TargetStatus.Done

    def mark_pending(self, target: Target) -> None:
        self.id_to_status[target.id] = TargetStatus.Pending

    def mark_running(self, target: Target) -> None:
        self.id_to_status[target.id] = TargetStatus.Running

    def all_done(self) -> bool:
        return all(status is TargetStatus.Done for status in self.id_to_status.values())

    def num_targets(self) -> int:
        return len(self.graph)

    def targets(self) -> set[Target]:
        return set(self.id_to_target.values())


prefix_format = "{timestamp:%H:%M:%S} {id} "
internal_format = "{timestamp:%H:%M:%S} "


class Controller:
    def __init__(self, config: Config, console: Console):
        self.config = config
        self.console = console
        self.live = Live(console=console, auto_refresh=False)

        self.graph = State.from_targets(self.config.targets)

        self.events: Fanout[Event] = Fanout()
        self.events_consumer = self.events.consumer()

        self.executions: dict[str, Execution] = {}
        self.waiters: dict[str, Task[Execution]] = {}
        self.watchers: dict[str, Task[None]] = {}
        self.heartbeat: Task[None] | None = None

    async def start(self) -> None:
        with self.live:
            try:
                await self.start_hearbeat()
                await self.start_watchers()
                await self.start_ready_targets()

                await self.control()
            finally:
                for watcher in self.watchers.values():
                    watcher.cancel()

                await wait(self.watchers.values(), timeout=1)

                for execution in self.executions.values():
                    await execution.terminate()

                await wait(self.waiters.values())

    async def control(self) -> None:
        while True:
            match event := await self.events_consumer.get():
                case CommandMessage() as msg:
                    self.console.print(self.render_command_message(msg))
                case CommandStarted(target=target) as msg:
                    self.console.print(self.render_started_message(msg))
                    self.graph.mark_running(target)
                case CommandExited(target=target) as msg:
                    self.console.print(self.render_exited_message(msg))

                    lifecycle = target.lifecycle
                    if isinstance(lifecycle, Restart):
                        self.graph.mark_pending(target)
                    else:
                        self.graph.mark_done(target)
                case WatchPathChanged(target=target) as msg:
                    self.console.print(self.render_watch_path_changed_message(msg))
                    self.graph.mark_pending(target)

            await self.start_ready_targets()

            self.live.update(self.info(event), refresh=True)

            if self.graph.all_done() and not self.watchers:
                return

    def info(self, event: Event) -> RenderableType:
        table = Table.grid()

        running_targets = self.graph.running_targets()
        if running_targets:
            running_targets_item = Text.assemble(
                "Running: ",
                Text(", ").join(Text(t.id, style=t.style) for t in running_targets),
            )
            rule_style = Style(color="green")
        else:
            running_targets_item = Text("Waiting...")
            rule_style = Style(color="yellow")

        table.add_row(
            internal_format.format_map({"timestamp": event.timestamp}), running_targets_item
        )

        return Group(Rule(style=rule_style), table)

    async def start_hearbeat(self) -> None:
        async def heartbeat() -> None:
            while True:
                await sleep(1 / 30)
                await self.events.put(Heartbeat())

        self.heartbeat = create_task(heartbeat())

    async def start_ready_targets(self) -> None:
        for t in self.graph.ready_targets():
            self.graph.mark_running(t)

            async def start() -> None:
                e = await Execution.start(
                    target=t,
                    command=t.commands[0],
                    events=self.events,
                    width=self.console.width - self.prefix_width,
                )
                self.executions[t.id] = e
                self.waiters[t.id] = create_task(e.wait())

            if isinstance(t.lifecycle, Restart) and t.id in self.executions:
                delay(t.lifecycle.delay, start)
            else:
                await start()

    async def start_watchers(self) -> None:
        for t in self.config.targets:
            if isinstance(t.lifecycle, Watch):
                self.watchers[t.id] = create_task(
                    watch(target=t, paths=t.lifecycle.paths, events=self.events)
                )

    def render_prefix(
        self, message: CommandMessage | CommandLifecycleEvent | WatchPathChanged
    ) -> str:
        return prefix_format.format_map(
            {"id": message.target.id, "timestamp": message.timestamp}
        ).ljust(self.prefix_width)

    def render_command_message(self, message: CommandMessage) -> RenderableType:
        prefix = Text.from_markup(
            self.render_prefix(message),
            style=Style.parse(message.target.style),
        )

        body = Text.from_ansi(message.text)

        g = Table.grid()
        g.add_row(prefix, body)

        return g

    def render_started_message(self, message: CommandStarted) -> RenderableType:
        prefix = Text.from_markup(
            self.render_prefix(message),
            style=Style.parse(message.target.style).chain(Style(dim=True)),
        )

        body = Text.assemble(
            "Command ",
            (message.command.args, message.target.style),
            " started",
            style=Style(dim=True),
        )

        g = Table.grid()
        g.add_row(prefix, body)

        return g

    def render_exited_message(self, message: CommandExited) -> RenderableType:
        prefix = Text.from_markup(
            self.render_prefix(message),
            style=Style.parse(message.target.style).chain(Style(dim=True)),
        )

        body = Text.assemble(
            "Command ",
            (message.command.args, message.target.style),
            " exited with code ",
            (str(message.exit_code), "green" if message.exit_code == 0 else "red"),
            style=Style(dim=True),
        )

        g = Table.grid()
        g.add_row(prefix, body)

        return g

    def render_watch_path_changed_message(self, message: WatchPathChanged) -> RenderableType:
        prefix = Text.from_markup(
            self.render_prefix(message),
            style=Style.parse(message.target.style).chain(Style(dim=True)),
        )

        changes = Text(", ").join(
            Text(path, style=CHANGE_TO_STYLE[change]) for change, path in message.changes
        )

        body = Text.assemble(
            "Running target ",
            (message.target.id, message.target.style),
            " due to detected changes: ",
            changes,
            style=Style(dim=True),
        )

        g = Table.grid()
        g.add_row(prefix, body)

        return g

    @cached_property
    def prefix_width(self) -> int:
        now = datetime.now()

        return len(
            max(
                (
                    prefix_format.format_map({"timestamp": now, "id": t.id})
                    for t in self.graph.targets()
                ),
                key=len,
            )
        )


CHANGE_TO_STYLE = {
    Change.added: Style(color="green"),
    Change.deleted: Style(color="red"),
    Change.modified: Style(color="yellow"),
}


async def watch(target: Target, paths: Iterable[Path], events: Fanout[Event]) -> None:
    try:
        async for changes in awatch(*paths):
            await events.put(WatchPathChanged(target=target, changes=changes))
    except RuntimeError:
        pass
