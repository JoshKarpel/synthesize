from __future__ import annotations

import os
from asyncio import Queue, Task, create_task
from asyncio.subprocess import PIPE, STDOUT, Process, create_subprocess_exec
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from signal import SIGKILL, SIGTERM
from stat import S_IEXEC
from time import monotonic

from synthesize.config import Args, Envs, ResolvedNode
from synthesize.messages import (
    Debug,
    ExecutionCompleted,
    ExecutionOutput,
    ExecutionStarted,
    Message,
)

OUTPUT_BUFFER_SIZE = 1 * 1024 * 1024  # 1 MiB, default is 64 KiB


def write_script(node: ResolvedNode, args: Args, tmp_dir: Path) -> Path:
    path = tmp_dir / f"{node.id}-{node.uid}"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        node.target.render(
            args=args
            | node.target.args
            | node.args
            | {
                "id": node.id,
            }
        )
    )
    path.chmod(path.stat().st_mode | S_IEXEC)

    return path


@dataclass(frozen=True)
class Execution:
    node: ResolvedNode

    events: Queue[Message] = field(repr=False)

    process: Process
    start_time: float
    reader: Task[None]

    @classmethod
    async def start(
        cls,
        node: ResolvedNode,
        args: Args,
        envs: Envs,
        tmp_dir: Path,
        width: int,
        events: Queue[Message],
    ) -> Execution:
        path = write_script(node=node, args=args, tmp_dir=tmp_dir)

        start_time = monotonic()

        process = await create_subprocess_exec(
            program=path,
            stdout=PIPE,
            stderr=STDOUT,
            env=os.environ
            | envs
            | node.target.envs
            | node.envs
            | {
                "FORCE_COLOR": "1",
                "COLUMNS": str(width),
            }
            | {
                "SYNTH_NODE_ID": node.id,
            },
            preexec_fn=os.setsid,
            limit=OUTPUT_BUFFER_SIZE,
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
            start_time=start_time,
            reader=reader,
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
        if self.has_exited:
            return None

        try:
            os.killpg(os.getpgid(self.process.pid), signal)
        except ProcessLookupError:
            # process exited before we could send the signal
            pass

    def terminate(self) -> None:
        self._send_signal(SIGTERM)

    def kill(self) -> None:
        self._send_signal(SIGKILL)

    async def wait(self) -> Execution:
        exit_code = await self.process.wait()
        end_time = monotonic()

        await self.reader

        await self.events.put(
            ExecutionCompleted(
                node=self.node,
                pid=self.pid,
                exit_code=exit_code,
                duration=timedelta(seconds=end_time - self.start_time),
            )
        )

        return self


async def read_output(node: ResolvedNode, process: Process, events: Queue[Message]) -> None:
    if process.stdout is None:  # pragma: unreachable
        raise Exception(f"{process} does not have an associated stream reader")

    while True:
        try:
            line = await process.stdout.readline()
        except ValueError:
            # Arises from a LimitOverrunError in readline(),
            # which is raised when the reader's internal buffer size is exceeded.
            await events.put(
                Debug(
                    node=node,
                    text=f"Command output buffer size exceeded for node {node.id!r}. Dropping command output buffer contents and continuing.",
                )
            )
            continue

        if not line:
            break

        await events.put(
            ExecutionOutput(
                node=node,
                text=line.decode("utf-8").rstrip(),
            )
        )


# need to track which trigger caused the node to run,
# because that changes the semantics of the restart
# the manager should protect itself from multiple restarts?
