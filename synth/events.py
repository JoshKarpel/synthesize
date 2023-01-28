import time

from pydantic import Field

from synth.config import Node
from synth.model import Model


class Event(Model):
    timestamp: float = Field(default_factory=time.time)


class CommandStarting(Event):
    node: Node


class CommandStarted(Event):
    node: Node


class CommandExited(Event):
    node: Node
    exit_code: int


class CommandMessage(Event):
    node: Node
    text: str
