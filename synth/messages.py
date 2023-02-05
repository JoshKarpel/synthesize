from datetime import datetime

from pydantic import Field
from watchfiles import Change

from synth.config import Target
from synth.model import Model


class Message(Model):
    timestamp: datetime = Field(default_factory=datetime.now)


class CommandLifecycleEvent(Message):
    target: Target
    pid: int


class TargetStarted(CommandLifecycleEvent):
    pass


class TargetExited(CommandLifecycleEvent):
    exit_code: int


class CommandMessage(Message):
    target: Target
    text: str


class WatchPathChanged(Message):
    target: Target
    changes: set[tuple[Change, str]]


class Heartbeat(Message):
    pass


class Quit(Message):
    pass
