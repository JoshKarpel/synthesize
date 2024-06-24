from __future__ import annotations

from typing import ClassVar, Type, TypeVar

import yaml
from pydantic import BaseModel, ConfigDict

C = TypeVar("C", bound="Model")


class Model(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        use_enum_values=True,
        extra="forbid",
        coerce_numbers_to_str=True,
    )

    @classmethod
    def parse_yaml(cls: Type[C], y: str) -> C:
        return cls.parse_obj(yaml.safe_load(y))

    def yaml(self) -> str:
        return yaml.dump(self.dict())
