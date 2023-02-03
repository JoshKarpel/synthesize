from datetime import datetime

from pydantic import Field
from watchfiles import Change

from synth.config import ShellCommand, Target
from synth.model import Model


class Message(Model):
    timestamp: datetime = Field(default_factory=datetime.now)


class CommandLifecycleEvent(Message):
    target: Target
    command: ShellCommand
    pid: int


class CommandStarted(CommandLifecycleEvent):
    pass


class CommandExited(CommandLifecycleEvent):
    exit_code: int


class CommandMessage(Message):
    target: Target
    command: ShellCommand
    text: str


class WatchPathChanged(Message):
    target: Target
    changes: set[tuple[Change, str]]


class Heartbeat(Message):
    pass


class Quit(Message):
    pass
