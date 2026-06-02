"""MemTable — sorted in-memory write buffer.

Uses a plain dict with on-demand sorted iteration via the built-in ``sorted()``.
Tombstones are represented as the sentinel ``TOMBSTONE``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

# Sentinel value that marks a deleted key.
TOMBSTONE = "\x00__TOMBSTONE__\x00"


class MemTable:
    """Mutable, sorted key/value buffer that holds the most recent writes.

    Keys and values are plain strings.  A deleted key is stored with the
    ``TOMBSTONE`` sentinel so that it can shadow older values in lower levels.

    Parameters
    ----------
    size_limit:
        Approximate number of bytes at which the caller should flush this
        table to an SSTable.  ``is_full()`` uses this threshold.
    """

    def __init__(self, size_limit: int = 4 * 1024 * 1024) -> None:
        self._data: dict[str, str] = {}
        self._size_bytes: int = 0
        self._size_limit = size_limit

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def put(self, key: str, value: str) -> None:
        """Insert or update *key* with *value*."""
        self._adjust_size(key, value)
        self._data[key] = value

    def delete(self, key: str) -> None:
        """Mark *key* as deleted by writing a tombstone."""
        self.put(key, TOMBSTONE)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get(self, key: str) -> str | None:
        """Return the value for *key*, or ``None`` if not present.

        Returns ``TOMBSTONE`` if the key has been deleted; the caller must
        check for this sentinel.
        """
        return self._data.get(key)

    def scan(self, start: str, end: str) -> list[tuple[str, str]]:
        """Return all key/value pairs with ``start <= key < end`` in sorted order."""
        return [(k, v) for k, v in sorted(self._data.items()) if start <= k < end]

    # ------------------------------------------------------------------
    # Iteration helpers
    # ------------------------------------------------------------------

    def items_sorted(self) -> Iterator[tuple[str, str]]:
        """Yield ``(key, value)`` pairs in ascending key order."""
        yield from sorted(self._data.items())

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._data)

    def is_full(self) -> bool:
        """Return ``True`` when accumulated bytes exceed *size_limit*."""
        return self._size_bytes >= self._size_limit

    def clear(self) -> None:
        """Reset the table (called after a successful flush to SSTable)."""
        self._data.clear()
        self._size_bytes = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _adjust_size(self, key: str, value: str) -> None:
        old_value = self._data.get(key)
        if old_value is not None:
            self._size_bytes -= len(key) + len(old_value)
        self._size_bytes += len(key) + len(value)
