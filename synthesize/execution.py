from __future__ import annotations

import os
from asyncio import Queue, Task, create_task
from asyncio.subprocess import PIPE, STDOUT, Process, create_subprocess_exec
from dataclasses import dataclass, field
from pathlib import Path
from signal import SIGKILL, SIGTERM
from stat import S_IEXEC

from synthesize.config import Args, Envs, FlowNode
from synthesize.messages import ExecutionCompleted, ExecutionOutput, ExecutionStarted, Message
from synthesize.utils import md5


def write_script(node: FlowNode, args: Args, tmp_dir: Path) -> Path:
    path = tmp_dir / f"{node.id}-{md5(node.model_dump_json().encode())}"

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
    node: FlowNode

    events: Queue[Message] = field(repr=False)

    process: Process
    reader: Task[None]

    @classmethod
    async def start(
        cls,
        node: FlowNode,
        args: Args,
        envs: Envs,
        tmp_dir: Path,
        width: int,
        events: Queue[Message],
    ) -> Execution:
        path = write_script(node=node, args=args, tmp_dir=tmp_dir)

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
        exit_code = await self.process.wait()

        await self.reader

        await self.events.put(
            ExecutionCompleted(
                node=self.node,
                pid=self.pid,
                exit_code=exit_code,
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
            ExecutionOutput(
                node=node,
                text=line.decode("utf-8").rstrip(),
            )
        )
