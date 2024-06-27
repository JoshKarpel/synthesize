from time import monotonic

import pytest

from synthesize.utils import delay, md5


async def test_delay() -> None:
    async def fn() -> str:
        return "hi"

    start = monotonic()

    assert await delay(0.1, fn) == "hi"

    assert monotonic() - start >= 0.1


@pytest.mark.parametrize(
    ("data", "expected"),
    (
        (b"", "d41d8cd98f00b204e9800998ecf8427e"),
        (b"hello", "5d41402abc4b2a76b9719d911017c592"),
    ),
)
def test_md5(data: bytes, expected: str) -> None:
    assert md5(data) == expected
