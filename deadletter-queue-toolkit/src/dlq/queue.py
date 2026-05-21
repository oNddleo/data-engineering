"""In-memory DLQ + replay driver.

The DLQ here is intentionally simple — a list of ``DeadLetter`` items
that you can append to, drain selectively (by failure kind, age, or
topic), and replay back to a handler. Production deployments swap
this for a Kafka/Pulsar/SQS-backed implementation; the interface
matters more than the storage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from dlq.schema import DeadLetter, FailureKind

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


class DeadLetterQueue:
    """In-memory DLQ.

    Not thread-safe — wrap in your own lock if needed.
    """

    __slots__ = ("_items",)

    def __init__(self) -> None:
        self._items: list[DeadLetter] = []

    # ----- mutation ------------------------------------------------------

    def append(self, dl: DeadLetter) -> None:
        self._items.append(dl)

    def extend(self, items: list[DeadLetter]) -> None:
        self._items.extend(items)

    def clear(self) -> None:
        self._items.clear()

    # ----- query ---------------------------------------------------------

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[DeadLetter]:
        return iter(self._items)

    def filter(
        self,
        *,
        kind: FailureKind | None = None,
        topic: str | None = None,
        min_age_ms: int | None = None,
    ) -> list[DeadLetter]:
        """Return matching items as a new list (doesn't drain the queue)."""
        out: list[DeadLetter] = []
        for dl in self._items:
            if kind is not None and dl.failure_kind != kind:
                continue
            if topic is not None and dl.original_topic != topic:
                continue
            if min_age_ms is not None and dl.age_ms < min_age_ms:
                continue
            out.append(dl)
        return out

    def counts_by_kind(self) -> dict[FailureKind, int]:
        counts: dict[FailureKind, int] = {k: 0 for k in FailureKind}
        for dl in self._items:
            counts[dl.failure_kind] += 1
        return counts

    # ----- replay --------------------------------------------------------

    def replay(
        self,
        handler: Callable[[DeadLetter], bool],
        *,
        kind: FailureKind | None = None,
    ) -> ReplayResult:
        """Re-run each (filtered) DLQ entry through ``handler``.

        The handler returns ``True`` on success (entry is removed from
        the DLQ) or ``False`` on failure (entry stays). Poison messages
        are typically skipped — pass ``kind=FailureKind.TRANSIENT`` etc.
        to scope the replay.
        """
        remaining: list[DeadLetter] = []
        n_replayed = 0
        n_succeeded = 0
        for dl in self._items:
            if kind is not None and dl.failure_kind != kind:
                remaining.append(dl)
                continue
            n_replayed += 1
            if handler(dl):
                n_succeeded += 1
            else:
                remaining.append(dl)
        self._items = remaining
        return ReplayResult(
            n_replayed=n_replayed,
            n_succeeded=n_succeeded,
            n_remaining=len(remaining),
        )


@dataclass(frozen=True, slots=True)
class ReplayResult:
    n_replayed: int
    n_succeeded: int
    n_remaining: int

    @property
    def success_rate(self) -> float:
        return self.n_succeeded / self.n_replayed if self.n_replayed else 0.0


__all__ = ["DeadLetterQueue", "ReplayResult"]
