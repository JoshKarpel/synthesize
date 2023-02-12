from __future__ import annotations

from asyncio import Task, create_task, sleep
from typing import Awaitable, Callable, Optional, TypeVar

T = TypeVar("T")


def delay(delay: float, fn: Callable[[], Awaitable[T]], name: Optional[str] = None) -> Task[T]:
    async def delayed() -> T:
        await sleep(delay)
        return await fn()

    return create_task(delayed(), name=name)
