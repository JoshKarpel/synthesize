import pytest

from synthesize.utils import hash_data


@pytest.mark.parametrize(
    ("data", "expected"),
    (
        (b"", "da39a3ee5e6b4b0d3255bfef95601890afd80709"),
        (b"hello", "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"),
    ),
)
def test_hash_data(data: bytes, expected: str) -> None:
    assert hash_data(data) == expected
