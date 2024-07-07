from datetime import datetime, timedelta

from pydantic import Field
from watchfiles import Change

from synthesize.config import ResolvedFlowNode
from synthesize.model import Model


class Message(Model):
    timestamp: datetime = Field(default_factory=datetime.now)


class ExecutionStarted(Message):
    node: ResolvedFlowNode
    pid: int


class ExecutionCompleted(Message):
    node: ResolvedFlowNode
    pid: int
    exit_code: int
    duration: timedelta


class ExecutionOutput(Message):
    node: ResolvedFlowNode
    text: str


class WatchPathChanged(Message):
    node: ResolvedFlowNode
    changes: set[tuple[Change, str]]


class Heartbeat(Message):
    pass


class Quit(Message):
    pass
