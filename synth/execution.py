from __future__ import annotations

import os
from asyncio import CancelledError, Task, create_task
from asyncio.subprocess import PIPE, STDOUT, Process, create_subprocess_shell
from dataclasses import dataclass, field
from signal import SIGKILL, SIGTERM

from synth.config import ShellCommand, Target
from synth.events import CommandExited, CommandMessage, CommandStarted, CommandStarting, Event
from synth.fanout import Fanout


@dataclass(frozen=True)
class Execution:
    target: Target
    command: ShellCommand

    events: Fanout[Event] = field(repr=False)

    process: Process
    reader: Task[None]

    width: int

    was_killed: bool = False

    @classmethod
    async def start(
        cls,
        target: Target,
        command: ShellCommand,
        events: Fanout[Event],
        width: int = 80,
    ) -> Execution:
        await events.put(CommandStarting(target=target, command=command))

        process = await create_subprocess_shell(
            cmd=command.args,
            stdout=PIPE,
            stderr=STDOUT,
            env={**os.environ, "FORCE_COLOR": "true", "COLUMNS": str(width)},
            preexec_fn=os.setsid,
        )

        reader = create_task(
            read_output(
                target=target,
                command=command,
                process=process,
                events=events,
            ),
            name=f"Read output for {command.args!r}",
        )

        await events.put(CommandStarted(target=target, command=command))

        return cls(
            target=target,
            command=command,
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

        # self.was_killed = True

        # await self.messages.put(
        #     InternalMessage(
        #         f"Terminating command: {self.config.command_string!r}", verbosity=Verbosity.INFO
        #     )
        # )

        self._send_signal(SIGTERM)

    async def kill(self) -> None:
        if self.has_exited:
            return None

        # self.was_killed = True

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

        await self.events.put(
            CommandExited(
                target=self.target,
                command=self.command,
                exit_code=self.exit_code,
            )
        )

        return self


async def read_output(
    target: Target, command: ShellCommand, process: Process, events: Fanout[Event]
) -> None:
    if process.stdout is None:  # pragma: unreachable
        raise Exception(f"{process} does not have an associated stream reader")

    while True:
        line = await process.stdout.readline()
        if not line:
            break

        await events.put(
            CommandMessage(
                target=target,
                command=command,
                text=line.decode("utf-8").rstrip(),
            )
        )
