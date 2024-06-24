from __future__ import annotations

import os
import shlex
import shutil
from asyncio import Queue, Task, create_task
from asyncio.subprocess import PIPE, STDOUT, Process, create_subprocess_exec
from dataclasses import dataclass, field
from functools import lru_cache
from hashlib import md5
from pathlib import Path
from signal import SIGKILL, SIGTERM
from stat import S_IEXEC

from synthesize.config import FlowNode
from synthesize.messages import CommandMessage, ExecutionCompleted, ExecutionStarted, Message


@lru_cache(maxsize=2**10)
def file_name(node: FlowNode) -> str:
    h = md5()
    h.update(node.id.encode())
    h.update(node.target.executable.encode())
    h.update(node.target.commands.encode())

    return f"{node.id}-{h.hexdigest()}"


@dataclass(frozen=True)
class Execution:
    node: FlowNode

    events: Queue[Message] = field(repr=False)

    process: Process
    reader: Task[None]

    width: int

    @classmethod
    async def start(
        cls,
        node: FlowNode,
        events: Queue[Message],
        tmp_dir: Path,
        width: int = 80,
    ) -> Execution:
        path = tmp_dir / file_name(node)
        path.parent.mkdir(parents=True, exist_ok=True)
        exe, *args = shlex.split(node.target.executable)
        which_exe = shutil.which(exe)
        if which_exe is None:
            raise Exception(f"Failed to find absolute path to executable for {exe}")
        path.write_text(
            "\n".join(
                (
                    f"#! {shlex.join((which_exe, *args))}",
                    "",
                    node.target.commands,
                )
            )
        )
        path.chmod(path.stat().st_mode | S_IEXEC)

        process = await create_subprocess_exec(
            program=path,
            stdout=PIPE,
            stderr=STDOUT,
            env={**os.environ, "FORCE_COLOR": "1", "COLUMNS": str(width)},
            preexec_fn=os.setsid,
        )

        reader = create_task(
            read_output(
                node=node,
                process=process,
                events=events,
            ),
            name=f"Read output for {node.id}",
        )

        await events.put(ExecutionStarted(node=node, pid=process.pid))

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
            ExecutionCompleted(
                node=self.node,
                pid=self.pid,
                exit_code=self.exit_code,
            )
        )

        return self


async def read_output(node: FlowNode, process: Process, events: Queue[Message]) -> None:
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
