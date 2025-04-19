from datetime import datetime, timedelta

from pydantic import Field
from watchfiles import Change

from synthesize.config import ResolvedNode
from synthesize.model import Model


class Message(Model):
    timestamp: datetime = Field(default_factory=datetime.now)


class ExecutionStarted(Message):
    node: ResolvedNode
    pid: int


class ExecutionCompleted(Message):
    node: ResolvedNode
    pid: int
    exit_code: int
    duration: timedelta


class ExecutionOutput(Message):
    node: ResolvedNode
    text: str


class WatchPathChanged(Message):
    node: ResolvedNode
    changes: set[tuple[Change, str]]


class Debug(Message):
    node: ResolvedNode | None
    text: str


class Heartbeat(Message):
    pass


class Quit(Message):
    pass
