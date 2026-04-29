from typing import Iterator, Sequence, TypeVar

T = TypeVar("T")


def batched(items: Sequence[T], size: int) -> Iterator[list[T]]:
    size = max(1, size)
    for idx in range(0, len(items), size):
        yield list(items[idx : idx + size])
