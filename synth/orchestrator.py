from __future__ import annotations

import signal
from asyncio import Queue, Task, create_task, gather, sleep
from collections.abc import Iterable
from pathlib import Path
from tempfile import TemporaryDirectory

from rich.console import Console
from watchfiles import awatch

from synth.config import Config, Restart, Target, Watch
from synth.execution import Execution
from synth.messages import Heartbeat, Message, Quit, TargetExited, TargetStarted, WatchPathChanged
from synth.renderer import Renderer
from synth.state import State
from synth.utils import delay


class Orchestrator:
    def __init__(self, config: Config, state: State, console: Console):
        self.config = config
        self.console = console
        self.state = state

        self.renderer = Renderer(state=state, console=console)

        self.inbox: Queue[Message] = Queue()

        self.executions: dict[str, Execution] = {}
        self.waiters: dict[str, Task[Execution]] = {}
        self.watchers: dict[str, Task[None]] = {}
        self.heartbeat: Task[None] | None = None

    async def start(self) -> None:
        if not self.state.targets():
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
                case TargetStarted(target=target):
                    self.state.mark_running(target)

                case TargetExited(target=target, exit_code=exit_code):
                    if isinstance(target.lifecycle, Restart):
                        self.state.mark_pending(target)
                    else:
                        if exit_code == 0:
                            self.state.mark_success(target)
                        else:
                            self.state.mark_failure(target)

                case WatchPathChanged(target=target):
                    if e := self.executions.get(target.id):
                        e.terminate()

                    self.state.mark_descendants_pending(target)

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
        for t in self.state.ready_targets():
            if e := self.executions.get(t.id):
                if not e.has_exited:
                    continue

            self.state.mark_running(t)

            async def start() -> None:
                e = await Execution.start(
                    target=t,
                    events=self.inbox,
                    width=self.console.width - self.renderer.prefix_width,
                    tmp_dir=tmp_dir,
                )
                self.executions[t.id] = e
                self.waiters[t.id] = create_task(e.wait())

            # When restarting after first execution, delay
            if isinstance(t.lifecycle, Restart) and t.id in self.executions:
                delay(t.lifecycle.delay, start)
            else:
                await start()

    async def start_watchers(self) -> None:
        for t in self.config.targets:
            if isinstance(t.lifecycle, Watch):
                self.watchers[t.id] = create_task(
                    watch(target=t, paths=t.lifecycle.paths, events=self.inbox)
                )


async def watch(target: Target, paths: Iterable[str | Path], events: Queue[Message]) -> None:
    try:
        async for changes in awatch(*paths):
            await events.put(WatchPathChanged(target=target, changes=changes))
    except RuntimeError:
        pass
