from __future__ import annotations

import signal
from asyncio import Queue, Task, create_task, gather, sleep
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory

from rich.console import Console
from watchfiles import awatch

from synthesize.config import Flow, FlowNode, Restart, Watch
from synthesize.execution import Execution
from synthesize.messages import (
    DoRestart,
    ExecutionCompleted,
    ExecutionStarted,
    Heartbeat,
    Message,
    Quit,
    WatchPathChanged,
)
from synthesize.renderer import Renderer
from synthesize.state import FlowState
from synthesize.utils import delay


class Orchestrator:
    def __init__(self, flow: Flow, console: Console):
        self.flow = flow
        self.console = console

        self.state = FlowState.from_flow(flow=flow)
        self.renderer = Renderer(state=self.state, console=console)

        self.inbox: Queue[Message] = Queue()

        self.executions: dict[str, Execution] = {}
        self.waiters: dict[str, Task[Execution]] = {}
        self.watchers: dict[str, Task[None]] = {}
        self.heartbeat: Task[None] | None = None

    async def run(self) -> None:
        if not self.flow.nodes:
            return

        with TemporaryDirectory(prefix="synth-") as tmpdir, self.renderer:
            tmp_dir = Path(tmpdir)

            try:
                await self.start_heartbeat()
                await self.start_watchers()
                await self.start_ready_targets(tmp_dir=tmp_dir)

                await self.handle_messages(tmp_dir=tmp_dir)
            finally:
                self.renderer.handle_shutdown_start()

                if self.heartbeat is not None:
                    self.heartbeat.cancel()

                for watcher in self.watchers.values():
                    watcher.cancel()

                await gather(*self.watchers.values(), return_exceptions=True)

                for execution in self.executions.values():
                    execution.terminate()

                await gather(*(e.wait() for e in self.executions.values()), return_exceptions=True)

                self.renderer.handle_shutdown_end()

    async def handle_messages(self, tmp_dir: Path) -> None:
        signal.signal(signal.SIGINT, lambda sig, frame: self.inbox.put_nowait(Quit()))

        while True:
            match message := await self.inbox.get():
                case ExecutionStarted(node=node):
                    self.state.mark_running(node)

                case ExecutionCompleted(node=node, exit_code=exit_code):
                    print("complete")
                    for t in node.triggers:
                        if isinstance(t, Restart):
                            if self.state.statuses[node.id] is not Status.Waiting:
                                self.state.mark_pending(node)
                            break
                    else:
                        if exit_code == 0:
                            self.state.mark_success(node)
                        else:
                            self.state.mark_failure(node)

                    self.state.mark_pending(*self.state.children(node))

                case WatchPathChanged(node=node):
                    if e := self.executions.get(node.id):
                        e.terminate()
                        self.state.mark_pending(node)

                case Quit():
                    return

            await self.start_ready_targets(tmp_dir=tmp_dir)

            self.renderer.handle_message(message)

            if self.state.all_done() and not self.watchers:
                return

    async def start_heartbeat(self) -> None:
        async def heartbeat() -> None:
            while True:
                await sleep(1 / 10)
                await self.inbox.put(Heartbeat())

        self.heartbeat = create_task(heartbeat())

    async def start_ready_targets(self, tmp_dir: Path) -> None:
        for node in self.state.ready_nodes():
            print(node)
            if e := self.executions.get(node.id):
                if not e.has_exited:
                    continue

            async def start() -> None:
                e = await Execution.start(
                    node=node,
                    args=self.flow.args,
                    envs=self.flow.envs,
                    tmp_dir=tmp_dir,
                    width=self.console.width - self.renderer.prefix_width,
                    events=self.inbox,
                )
                self.executions[node.id] = e
                self.waiters[node.id] = create_task(e.wait())

            # When restarting after first execution, delay
            for t in node.triggers:
                if isinstance(t, Restart) and node.id in self.executions:
                    print("HI")
                    # TODO: starting too many times with multiple triggers!
                    self.state.mark(node, status=Status.Waiting)
                    delay(t.delay, start)
                    break
            else:
                print("ALSO HI?")
                self.state.mark(node, status=Status.Waiting)
                await start()

    async def start_watchers(self) -> None:
        for node in self.flow.nodes.values():
            for trigger in node.triggers:
                if isinstance(trigger, Watch):
                    self.watchers[node.id] = create_task(
                        watch(
                            node=node,
                            paths=trigger.paths,
                            events=self.inbox,
                        )
                    )


async def watch(node: FlowNode, paths: Iterable[str | Path], events: Queue[Message]) -> None:
    async for changes in awatch(*paths):
        await events.put(WatchPathChanged(node=node, changes=changes))


class Status(Enum):
    Pending = "pending"
    Waiting = "waiting"
    Starting = "starting"
    Running = "running"
    Succeeded = "succeeded"
    Failed = "failed"


@dataclass(slots=True)
class NodeState:
    flow: Flow
    node: FlowNode

    tmp_dir: Path
    width: int

    state: Status = Status.Pending
    execution: Execution | None = None
    waiter: Task[None] | None = None
    restart: Task[None] | None = None

    inbox: Queue[Message] = field(default_factory=Queue)

    async def handle_messages(self, message: Message) -> None:
        while True:
            match self.state, await self.inbox.get():
                case Status.Pending, WatchPathChanged() | DoRestart():
                    await self.start()
                    self.state = Status.Starting
                case Status.Starting, ExecutionStarted():
                    self.state = Status.Running
                case Status.Starting, _:
                    pass
                case Status.Running, ExecutionCompleted(exit_code=exit_code):
                    self.state = Status.Succeeded if exit_code == 0 else Status.Failed
                    for t in self.node.triggers:
                        if isinstance(t, Restart):

                            async def restart() -> None:
                                await sleep(t.delay)
                                await self.inbox.put(DoRestart())

                            self.restart = create_task(restart())
                            break
                case state, message:
                    raise Exception(f"Unhandled message {message} in state {state}")

    async def start(self) -> None:
        # TODO: what if it gets stuck?
        if self.execution is not None:
            self.execution.terminate()
            await self.waiter

        new_execution = await Execution.start(
            node=self.node,
            args=self.flow.args,
            envs=self.flow.envs,
            tmp_dir=self.tmp_dir,
            width=self.width,
            # width=self.console.width - self.renderer.prefix_width,
            events=self.inbox,
        )

        self.execution = new_execution
        self.waiter = create_task(new_execution.wait())
