from __future__ import annotations

import os
from asyncio import Queue, Task, create_task
from asyncio.subprocess import PIPE, STDOUT, Process, create_subprocess_shell
from dataclasses import dataclass, field
from signal import SIGKILL, SIGTERM

from synth.config import ShellCommand, Target
from synth.messages import CommandExited, CommandMessage, CommandStarted, Message


@dataclass(frozen=True)
class Execution:
    target: Target
    idx: int

    events: Queue[Message] = field(repr=False)

    process: Process
    reader: Task[None]

    width: int

    @classmethod
    async def start(
        cls,
        target: Target,
        idx: int,
        events: Queue[Message],
        width: int = 80,
    ) -> Execution:
        command = target.commands[idx]

        process = await create_subprocess_shell(
            cmd=command.args,
            stdout=PIPE,
            stderr=STDOUT,
            env={**os.environ, "FORCE_COLOR": "1", "COLUMNS": str(width)},
            preexec_fn=os.setsid,
            executable=os.getenv("SHELL"),
        )

        reader = create_task(
            read_output(
                target=target,
                command=command,
                idx=idx,
                process=process,
                events=events,
            ),
            name=f"Read output for {command!r}",
        )

        await events.put(CommandStarted(target=target, command=command, idx=idx, pid=process.pid))

        return cls(
            target=target,
            idx=idx,
            events=events,
            process=process,
            reader=reader,
            width=width,
        )

    @property
    def command(self) -> ShellCommand:
        return self.target.commands[self.idx]

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

    def terminate(self) -> None:
        if self.has_exited:
            return None

        self._send_signal(SIGTERM)

    def kill(self) -> None:
        if self.has_exited:
            return None

        self._send_signal(SIGKILL)

    async def wait(self) -> Execution:
        await self.process.wait()

        await self.reader

        await self.events.put(
            CommandExited(
                target=self.target,
                command=self.command,
                idx=self.idx,
                pid=self.pid,
                exit_code=self.exit_code,
            )
        )

        return self


async def read_output(
    target: Target, command: ShellCommand, idx: int, process: Process, events: Queue[Message]
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
                idx=idx,
                text=line.decode("utf-8").rstrip(),
            )
        )
