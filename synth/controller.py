from rich.console import Console

from synth.config import Config
from synth.events import Event
from synth.execution import Execution
from synth.fanout import Fanout


class Controller:
    def __init__(self, config: Config, console: Console):
        self.config = config
        self.console = console

        self.events: Fanout[Event] = Fanout()
        self.events_consumer = self.events.consumer()

    async def start(self) -> None:
        for node in self.config.graph.nodes:
            e = await Execution.start(node=node, events=self.events, width=80)
            print(e)
            await e.wait()
