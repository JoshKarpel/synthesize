import time

from pydantic import Field

from synth.config import ShellCommand, Target
from synth.model import Model


class Event(Model):
    timestamp: float = Field(default_factory=time.time)


class CommandStarting(Event):
    target: Target
    command: ShellCommand


class CommandStarted(Event):
    target: Target
    command: ShellCommand


class CommandExited(Event):
    target: Target
    command: ShellCommand


class CommandMessage(Event):
    target: Target
    command: ShellCommand
    text: str
