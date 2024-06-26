from __future__ import annotations

import hashlib
from asyncio import Task, create_task, sleep
from typing import Annotated, Any, Awaitable, Callable, Optional, TypeVar

from frozendict import frozendict
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema
from pydantic_core.core_schema import (
    chain_schema,
    dict_schema,
    is_instance_schema,
    json_or_python_schema,
    no_info_plain_validator_function,
    plain_serializer_function_ser_schema,
    union_schema,
)

T = TypeVar("T")


def delay(delay: float, fn: Callable[[], Awaitable[T]], name: Optional[str] = None) -> Task[T]:
    async def delayed() -> T:
        await sleep(delay)
        return await fn()

    return create_task(delayed(), name=name)


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


# https://github.com/pydantic/pydantic/discussions/8721
class _PydanticFrozenDictAnnotation:
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        from_dict_schema = chain_schema(
            [dict_schema(), no_info_plain_validator_function(frozendict)]
        )
        return json_or_python_schema(
            json_schema=from_dict_schema,
            python_schema=union_schema([is_instance_schema(frozendict), from_dict_schema]),
            serialization=plain_serializer_function_ser_schema(dict),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return handler(dict_schema())


_K = TypeVar("_K")
_V = TypeVar("_V")
FrozenDict = Annotated[frozendict[_K, _V], _PydanticFrozenDictAnnotation]
