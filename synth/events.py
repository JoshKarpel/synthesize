from datetime import datetime

from pydantic import Field
from watchfiles import Change

from synth.config import ShellCommand, Target
from synth.model import Model


class Event(Model):
    timestamp: datetime = Field(default_factory=datetime.now)


class CommandLifecycleEvent(Event):
    target: Target
    command: ShellCommand


class CommandStarted(CommandLifecycleEvent):
    pass


class CommandExited(CommandLifecycleEvent):
    exit_code: int


class CommandMessage(Event):
    target: Target
    command: ShellCommand
    text: str


class WatchPathChanged(Event):
    target: Target
    changes: set[tuple[Change, str]]


class Heartbeat(Event):
    pass
