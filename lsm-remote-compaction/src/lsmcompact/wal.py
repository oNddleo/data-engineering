"""Write-Ahead Log (WAL).

Appends one JSON line per write operation to a ``.wal`` file.  On startup the
WAL is replayed to reconstruct any writes that were not yet flushed to an
SSTable.

Record format (one per line):
    {"op": "put"|"delete", "k": "<key>", "v": "<value>"}

For ``delete`` operations the value field is omitted / set to the tombstone.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class WAL:
    """Append-only Write-Ahead Log backed by a plain JSONL file.

    Parameters
    ----------
    path:
        File path for the WAL.  Created if it does not exist.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        # Open in append mode so each write is durable.
        self._fh = path.open("a", encoding="utf-8")

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def append_put(self, key: str, value: str) -> None:
        """Record a PUT operation."""
        self._write({"op": "put", "k": key, "v": value})

    def append_delete(self, key: str) -> None:
        """Record a DELETE operation."""
        self._write({"op": "delete", "k": key, "v": ""})

    def _write(self, record: dict[str, str]) -> None:
        self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._fh.flush()

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    def recover(self) -> Iterator[tuple[str, str, str]]:
        """Yield ``(op, key, value)`` tuples for every record in the WAL.

        Safe to call even if the file does not exist yet, or has partial last
        lines (those are skipped silently).
        """
        if not self._path.exists():
            return
        with self._path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    # Partial/corrupt line — skip it.
                    continue
                op = str(rec.get("op", ""))
                key = str(rec.get("k", ""))
                value = str(rec.get("v", ""))
                if op in ("put", "delete") and key:
                    yield op, key, value

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def truncate(self) -> None:
        """Delete WAL content (called after a successful MemTable flush)."""
        self._fh.close()
        self._path.write_text("", encoding="utf-8")
        self._fh = self._path.open("a", encoding="utf-8")

    def close(self) -> None:
        """Flush and close the underlying file handle."""
        self._fh.flush()
        self._fh.close()

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> WAL:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
