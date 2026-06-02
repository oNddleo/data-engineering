"""SSTable — immutable sorted-string table written to disk.

File format (JSONL, one entry per line):
    {"k": "<key>", "v": "<value>"}

The file is always written in ascending key order.  After the data rows a
single metadata line is appended:
    {"__meta__": true, "bloom": [<hex hashes...>], "index": [[key, offset], ...]}

* **Bloom filter** — two SHA-256 probes mapped into a bit-array of *m* bits.
* **Sparse index** — every ``INDEX_STRIDE``-th key is stored with its byte
  offset so we can skip to roughly the right region during point lookups.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import io
    from collections.abc import Iterator
    from pathlib import Path

INDEX_STRIDE = 16  # record one index entry every N keys
BLOOM_BITS = 1 << 14  # 16 384 bits (~2 KB)


# ---------------------------------------------------------------------------
# Bloom filter helpers
# ---------------------------------------------------------------------------


def _bloom_hashes(key: str, m: int) -> tuple[int, int]:
    """Return two independent hash values in ``[0, m)``."""
    digest = hashlib.sha256(key.encode()).digest()
    h1 = int.from_bytes(digest[:8], "big") % m
    h2 = int.from_bytes(digest[8:16], "big") % m
    return h1, h2


class BloomFilter:
    """A simple two-hash bloom filter backed by a Python ``bytearray``."""

    def __init__(self, m: int = BLOOM_BITS) -> None:
        self._m = m
        self._bits = bytearray(m // 8 + 1)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add(self, key: str) -> None:
        for h in _bloom_hashes(key, self._m):
            self._bits[h >> 3] |= 1 << (h & 7)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        for h in _bloom_hashes(key, self._m):
            if not (self._bits[h >> 3] & (1 << (h & 7))):
                return False
        return True

    # ------------------------------------------------------------------
    # Serialisation helpers used by SSTable writer
    # ------------------------------------------------------------------

    def to_hex(self) -> str:
        return self._bits.hex()

    @classmethod
    def from_hex(cls, hex_str: str, m: int = BLOOM_BITS) -> BloomFilter:
        obj = cls.__new__(cls)
        obj._m = m
        obj._bits = bytearray.fromhex(hex_str)
        return obj


# ---------------------------------------------------------------------------
# SSTable writer
# ---------------------------------------------------------------------------


class SSTableWriter:
    """Writes an SSTable from a stream of ``(key, value)`` pairs.

    The pairs **must** arrive in ascending key order.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._bloom = BloomFilter()
        self._index: list[tuple[str, int]] = []
        self._count = 0
        self._fh: io.TextIOWrapper | None = None

    def __enter__(self) -> SSTableWriter:
        self._fh = self._path.open("w", encoding="utf-8")
        return self

    def __exit__(self, *_: object) -> None:
        self._flush_meta()
        if self._fh is not None:
            self._fh.close()

    def write(self, key: str, value: str) -> None:
        if self._fh is None:
            raise RuntimeError("SSTableWriter must be used as a context manager")
        if self._count % INDEX_STRIDE == 0:
            self._index.append((key, self._fh.tell()))
        self._bloom.add(key)
        line = json.dumps({"k": key, "v": value}, ensure_ascii=False) + "\n"
        self._fh.write(line)
        self._count += 1

    def _flush_meta(self) -> None:
        if self._fh is None:
            return
        meta = {
            "__meta__": True,
            "bloom": self._bloom.to_hex(),
            "index": [[k, off] for k, off in self._index],
        }
        self._fh.write(json.dumps(meta) + "\n")


# ---------------------------------------------------------------------------
# SSTable reader
# ---------------------------------------------------------------------------


class SSTable:
    """Read-only view of a previously written SSTable file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._bloom: BloomFilter | None = None
        self._index: list[tuple[str, int]] = []
        self._meta_offset: int = 0
        self._load_meta()

    # ------------------------------------------------------------------
    # Metadata loading
    # ------------------------------------------------------------------

    def _load_meta(self) -> None:
        """Read the last line of the file to populate bloom + sparse index."""
        with self.path.open("rb") as fh:
            # Seek backwards to find the final newline-terminated JSON line.
            fh.seek(0, 2)
            file_size = fh.tell()
            if file_size == 0:
                return
            # Walk back to find the start of the last line.
            pos = file_size - 2
            while pos > 0:
                fh.seek(pos)
                ch = fh.read(1)
                if ch == b"\n":
                    self._meta_offset = pos + 1
                    break
                pos -= 1
            else:
                self._meta_offset = 0
            fh.seek(self._meta_offset)
            raw = fh.read().decode("utf-8").strip()
        try:
            meta = json.loads(raw)
        except json.JSONDecodeError:
            return
        if not isinstance(meta, dict) or not meta.get("__meta__"):
            return
        self._bloom = BloomFilter.from_hex(meta["bloom"])
        self._index = [(row[0], row[1]) for row in meta["index"]]

    # ------------------------------------------------------------------
    # Point lookup
    # ------------------------------------------------------------------

    def get(self, key: str) -> str | None:
        """Return the value for *key*, or ``None`` if not found.

        Uses the bloom filter and sparse index to minimise I/O.
        """
        if self._bloom is not None and key not in self._bloom:
            return None
        seek_to = self._find_seek_offset(key)
        with self.path.open("r", encoding="utf-8") as fh:
            fh.seek(seek_to)
            for raw in fh:
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if rec.get("__meta__"):
                    break
                k = rec["k"]
                if k == key:
                    return str(rec["v"])
                if k > key:
                    break
        return None

    # ------------------------------------------------------------------
    # Iteration
    # ------------------------------------------------------------------

    def items(self) -> Iterator[tuple[str, str]]:
        """Yield ``(key, value)`` pairs in sorted order (tombstones included)."""
        with self.path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if rec.get("__meta__"):
                    break
                yield str(rec["k"]), str(rec["v"])

    def scan(self, start: str, end: str) -> list[tuple[str, str]]:
        """Return all pairs with ``start <= key < end`` in sorted order."""
        seek_to = self._find_seek_offset(start)
        result: list[tuple[str, str]] = []
        with self.path.open("r", encoding="utf-8") as fh:
            fh.seek(seek_to)
            for raw in fh:
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if rec.get("__meta__"):
                    break
                k = str(rec["k"])
                if k >= end:
                    break
                if k >= start:
                    result.append((k, str(rec["v"])))
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_seek_offset(self, key: str) -> int:
        """Return the byte offset to seek to before scanning for *key*."""
        if not self._index:
            return 0
        # Binary search for the largest index key <= search key.
        lo, hi = 0, len(self._index) - 1
        result = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            idx_key, idx_off = self._index[mid]
            if idx_key <= key:
                result = idx_off
                lo = mid + 1
            else:
                hi = mid - 1
        return result

    def __contains__(self, key: object) -> bool:
        """Bloom-filter membership test (may have false positives)."""
        if not isinstance(key, str):
            return False
        if self._bloom is None:
            return True  # unknown — assume possibly present
        return key in self._bloom
