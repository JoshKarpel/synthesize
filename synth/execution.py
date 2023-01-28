from __future__ import annotations

import os
from asyncio import CancelledError, Task, create_task
from asyncio.subprocess import PIPE, STDOUT, Process, create_subprocess_shell
from dataclasses import dataclass, field
from signal import SIGKILL, SIGTERM

from synth.config import Node
from synth.events import CommandExited, CommandMessage, CommandStarted, CommandStarting, Event
from synth.fanout import Fanout


@dataclass
class Execution:
    node: Node

    events: Fanout[Event] = field(repr=False)

    process: Process
    reader: Task[None]

    width: int

    was_killed: bool = False

    @classmethod
    async def start(
        cls,
        node: Node,
        events: Fanout[Event],
        width: int = 80,
    ) -> Execution:
        await events.put(CommandStarting(node=node))

        process = await create_subprocess_shell(
            cmd=node.command,
            stdout=PIPE,
            stderr=STDOUT,
            env={**os.environ, "FORCE_COLOR": "true", "COLUMNS": str(width)},
            preexec_fn=os.setsid,
        )

        reader = create_task(
            read_output(node=node, process=process, events=events),
            name=f"Read output for {node.command!r}",
        )

        await events.put(CommandStarted(node=node))

        return cls(
            node=node,
            events=events,
            process=process,
            reader=reader,
            width=width,
        )

    @property
    def pid(self) -> int:
        return self.process.pid

    @property
    def exit_code(self) -> int | None:
        return self.process.returncode

    @property
    def has_exited(self) -> bool:
        return self.exit_code is not None

    def _send_signal(self, signal: int) -> None:
        os.killpg(os.getpgid(self.process.pid), signal)

    async def terminate(self) -> None:
        if self.has_exited:
            return None

        self.was_killed = True

        # await self.messages.put(
        #     InternalMessage(
        #         f"Terminating command: {self.config.command_string!r}", verbosity=Verbosity.INFO
        #     )
        # )

        self._send_signal(SIGTERM)

    async def kill(self) -> None:
        if self.has_exited:
            return None

        self.was_killed = True

        # await self.messages.put(
        #     InternalMessage(
        #         f"Killing command: {self.config.command_string!r}", verbosity=Verbosity.INFO
        #     )
        # )INFO

        self._send_signal(SIGKILL)

    async def wait(self) -> Execution:
        await self.process.wait()

        try:
            await self.reader
        except CancelledError:
            pass

        await self.events.put(CommandExited(node=self.node, exit_code=self.exit_code))

        return self


async def read_output(node: Node, process: Process, events: Fanout[Event]) -> None:
    if process.stdout is None:  # pragma: unreachable
        raise Exception(f"{process} does not have an associated stream reader")

    while True:
        line = await process.stdout.readline()
        if not line:
            break

        await events.put(
            CommandMessage(
                node=node,
                text=line.decode("utf-8").rstrip(),
            )
        )
