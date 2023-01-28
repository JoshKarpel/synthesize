from __future__ import annotations

from asyncio import Queue, gather
from dataclasses import dataclass, field
from typing import Generic, List, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Fanout(Generic[T]):
    queues: List[Queue[T]] = field(default_factory=list)

    async def put(self, item: T) -> None:
        await gather(*(q.put(item) for q in self.queues))

    def put_nowait(self, item: T) -> None:
        for q in self.queues:
            q.put_nowait(item)

    def consumer(self) -> Queue[T]:
        q: Queue[T] = Queue()

        self.queues.append(q)

        return q
