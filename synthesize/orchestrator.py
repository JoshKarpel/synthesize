from __future__ import annotations

import signal
from asyncio import Queue, Task, create_task, gather, sleep
from collections.abc import Iterable
from pathlib import Path
from tempfile import TemporaryDirectory

from rich.console import Console
from watchfiles import awatch

from synthesize.config import Flow, FlowNode, Restart, Watch
from synthesize.execution import Execution
from synthesize.messages import (
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
        if not self.state.nodes():
            return

        with TemporaryDirectory(prefix="snyth-") as tmpdir, self.renderer:
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
                    if isinstance(node.trigger, Restart):
                        self.state.mark_pending(node)
                    else:
                        if exit_code == 0:
                            self.state.mark_success(node)
                        else:
                            self.state.mark_failure(node)

                case WatchPathChanged(node=node):
                    if e := self.executions.get(node.id):
                        e.terminate()

                    self.state.mark_descendants_pending(node)

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
        for ready_node in self.state.ready_nodes():
            if e := self.executions.get(ready_node.id):
                if not e.has_exited:
                    continue

            self.state.mark_running(ready_node)

            async def start() -> None:
                e = await Execution.start(
                    node=ready_node,
                    events=self.inbox,
                    width=self.console.width - self.renderer.prefix_width,
                    tmp_dir=tmp_dir,
                )
                self.executions[ready_node.id] = e
                self.waiters[ready_node.id] = create_task(e.wait())

            # When restarting after first execution, delay
            if isinstance(ready_node.trigger, Restart) and ready_node.id in self.executions:
                delay(ready_node.trigger.delay, start)
            else:
                await start()

    async def start_watchers(self) -> None:
        for node in self.flow.values():
            if isinstance(node.trigger, Watch):
                self.watchers[node.id] = create_task(
                    watch(
                        node=node,
                        paths=node.trigger.paths,
                        events=self.inbox,
                    )
                )


async def watch(node: FlowNode, paths: Iterable[str | Path], events: Queue[Message]) -> None:
    async for changes in awatch(*paths):
        await events.put(WatchPathChanged(node=node, changes=changes))
