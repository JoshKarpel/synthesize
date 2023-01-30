from __future__ import annotations

from asyncio import Task, create_task
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from networkx import DiGraph
from rich.console import Console, RenderableType
from rich.style import Style
from rich.table import Table
from rich.text import Text

from synth.config import Config, Target
from synth.events import CommandExited, CommandMessage, CommandStarted, Event
from synth.execution import Execution
from synth.fanout import Fanout


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


prefix_format = "{timestamp:%H:%M:%S} {id} "


class Controller:
    def __init__(self, config: Config, console: Console):
        self.config = config
        self.console = console

        self.graph = State.from_targets(self.config.targets)

        self.events: Fanout[Event] = Fanout()
        self.events_consumer = self.events.consumer()

        self.executions: dict[str, Execution] = {}
        self.waiters: dict[str, Task[Execution]] = {}

    async def start(self) -> None:
        await self.start_ready_targets()

        while True:
            match await self.events_consumer.get():
                case CommandMessage() as msg:
                    self.console.print(self.render_command_message(msg))
                case CommandStarted() as msg:
                    self.console.print(self.render_started_message(msg))
                case CommandExited(target=target) as msg:
                    self.console.print(self.render_exited_message(msg))
                    self.graph.mark_done(target)
                    await self.start_ready_targets()

            if self.graph.all_done():
                break

    async def start_ready_targets(self) -> None:
        for t in self.graph.ready_targets():
            self.graph.mark_running(t)
            e = await Execution.start(
                target=t,
                command=t.commands[0],
                events=self.events,
                width=80,
            )
            self.executions[t.id] = e
            self.waiters[t.id] = create_task(e.wait())

    def render_command_message(self, message: CommandMessage) -> RenderableType:
        prefix = Text.from_markup(
            prefix_format.format_map({"id": message.target.id, "timestamp": message.timestamp}),
            style=Style.parse(message.target.style),
        )

        body = Text.from_ansi(message.text)

        g = Table.grid()
        g.add_row(prefix, body)

        return g

    def render_started_message(self, message: CommandStarted) -> RenderableType:
        prefix = Text.from_markup(
            prefix_format.format_map({"id": message.target.id, "timestamp": message.timestamp}),
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
            prefix_format.format_map({"id": message.target.id, "timestamp": message.timestamp}),
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
