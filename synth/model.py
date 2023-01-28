from __future__ import annotations

from typing import Type, TypeVar

import yaml
from pydantic import BaseModel

C = TypeVar("C")


class Model(BaseModel, frozen=True, use_enum_values=True):
    @classmethod
    def parse_yaml(cls: Type[C], y: str) -> C:
        return cls.parse_obj(yaml.safe_load(y))

    def yaml(self) -> str:
        return yaml.dump(self.dict())
