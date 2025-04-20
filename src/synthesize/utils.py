from __future__ import annotations

import hashlib
from typing import TypeVar

T = TypeVar("T")


def hash_data(data: bytes | str) -> str:
    return hashlib.sha1(data if isinstance(data, bytes) else data.encode()).hexdigest()
