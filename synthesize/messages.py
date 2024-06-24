from datetime import datetime

from pydantic import Field
from watchfiles import Change

from synthesize.config import FlowNode
from synthesize.model import Model


class Message(Model):
    timestamp: datetime = Field(default_factory=datetime.now)


class CommandLifecycleEvent(Message):
    node: FlowNode
    pid: int


class ExecutionStarted(CommandLifecycleEvent):
    pass


class ExecutionCompleted(CommandLifecycleEvent):
    exit_code: int


class CommandMessage(Message):
    node: FlowNode
    text: str


class WatchPathChanged(Message):
    node: FlowNode
    changes: set[tuple[Change, str]]


class Heartbeat(Message):
    pass


class Quit(Message):
    pass
