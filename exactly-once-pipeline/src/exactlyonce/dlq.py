"""DeadLetterQueue: in-memory + JSONL-backed dead-letter queue."""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class DLQEntry:
    """A single dead-letter queue record."""

    dlq_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event: dict[str, object] = field(default_factory=dict)
    reason: str = ""
    source_consumer: str = ""
    enqueued_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> DLQEntry:
        return cls(
            dlq_id=str(data.get("dlq_id", str(uuid.uuid4()))),
            event=dict(data.get("event", {})),  # type: ignore[call-overload]
            reason=str(data.get("reason", "")),
            source_consumer=str(data.get("source_consumer", "")),
            enqueued_at=str(data.get("enqueued_at", datetime.now(tz=UTC).isoformat())),
        )


class DeadLetterQueue:
    """Thread-safe dead-letter queue with optional JSONL persistence."""

    def __init__(self, persistence_path: Path | None = None) -> None:
        self._entries: list[DLQEntry] = []
        self._lock = threading.Lock()
        self._path = persistence_path
        if persistence_path is not None:
            self._load(persistence_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue(
        self,
        event: dict[str, object],
        reason: str,
        source_consumer: str = "",
    ) -> DLQEntry:
        """Add a failed event to the dead-letter queue."""
        entry = DLQEntry(event=dict(event), reason=reason, source_consumer=source_consumer)
        with self._lock:
            self._entries.append(entry)
            if self._path is not None:
                self._append(entry)
        return entry

    def drain(self, max: int = 100) -> list[DLQEntry]:
        """Remove and return up to *max* entries from the front of the queue."""
        with self._lock:
            batch = self._entries[:max]
            self._entries = self._entries[max:]
            if self._path is not None:
                self._flush()
            return batch

    def count(self) -> int:
        """Return the number of entries currently in the queue."""
        with self._lock:
            return len(self._entries)

    def all_entries(self) -> list[DLQEntry]:
        """Return a snapshot of all entries without removing them."""
        with self._lock:
            return list(self._entries)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self, path: Path) -> None:
        if not path.exists():
            return
        with path.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data: dict[str, object] = json.loads(line)
                    entry = DLQEntry.from_dict(data)
                    self._entries.append(entry)
                except (json.JSONDecodeError, KeyError):
                    continue

    def _append(self, entry: DLQEntry) -> None:
        assert self._path is not None
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")

    def _flush(self) -> None:
        """Rewrite the JSONL file with remaining entries (called under lock)."""
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w") as fh:
            for entry in self._entries:
                fh.write(json.dumps(entry.to_dict()) + "\n")
