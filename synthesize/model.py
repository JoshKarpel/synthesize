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
    def model_validate_yaml(cls: Type[C], y: str) -> C:
        return cls.model_validate(yaml.safe_load(y))
