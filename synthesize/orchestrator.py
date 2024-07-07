from __future__ import annotations

import signal
from asyncio import Queue, Task, create_task, gather, get_running_loop, sleep
from collections.abc import Iterable
from pathlib import Path
from tempfile import TemporaryDirectory

from rich.console import Console
from watchfiles import awatch

from synthesize.config import ResolvedFlow, ResolvedNode, Restart, Watch
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
from synthesize.state import FlowState, Status


class Orchestrator:
    def __init__(self, flow: ResolvedFlow, console: Console):
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
                    if self.state.statuses[node.id] is not Status.Pending:
                        for t in node.triggers:
                            if isinstance(t, Restart):
                                if self.state.statuses[node.id] is not Status.Waiting:
                                    self.state.mark(node, status=Status.Waiting)

                                    def waiting_to_pending() -> None:
                                        if self.state.statuses[node.id] is Status.Waiting:
                                            self.state.mark_pending(node)

                                    get_running_loop().call_later(t.delay, waiting_to_pending)
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
            if e := self.executions.get(node.id):
                if not e.has_exited:
                    continue

            self.state.mark(node, status=Status.Waiting)

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

    async def start_watchers(self) -> None:
        for node in self.flow.nodes.values():
            for trigger in node.triggers:
                if isinstance(trigger, Watch):
                    self.watchers[node.id] = create_task(
                        watch(
                            node=node,
                            paths=trigger.watch,
                            events=self.inbox,
                        )
                    )


async def watch(node: ResolvedNode, paths: Iterable[str | Path], events: Queue[Message]) -> None:
    async for changes in awatch(*paths):
        await events.put(WatchPathChanged(node=node, changes=changes))
