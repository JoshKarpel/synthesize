from dataclasses import dataclass

from rich.console import Console

from synth.config import Config, Target
from synth.events import Event
from synth.fanout import Fanout


@dataclass(frozen=True)
class TargetGraph:
    targets: set[Target]


class Controller:
    def __init__(self, config: Config, console: Console):
        self.config = config
        self.console = console

        self.events: Fanout[Event] = Fanout()
        self.events_consumer = self.events.consumer()

    async def start(self) -> None:
        pass
