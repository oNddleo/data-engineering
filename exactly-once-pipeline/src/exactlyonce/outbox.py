"""OutboxStore: pending/published state machine with JSONL persistence."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class OutboxEntry:
    """A single outbox record."""

    event_id: str
    payload: dict[str, object]
    status: Literal["PENDING", "PUBLISHED", "FAILED"] = "PENDING"
    created_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    published_at: str | None = None
    retry_count: int = 0

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> OutboxEntry:
        return cls(
            event_id=str(data["event_id"]),
            payload=dict(data["payload"]),  # type: ignore[call-overload]
            status=data.get("status", "PENDING"),  # type: ignore[arg-type]
            created_at=str(data.get("created_at", datetime.now(tz=UTC).isoformat())),
            published_at=data.get("published_at") and str(data["published_at"]) or None,  # type: ignore[arg-type]
            retry_count=int(data.get("retry_count", 0)),  # type: ignore[call-overload]
        )


class OutboxStore:
    """Thread-safe transactional outbox backed by in-memory dict + optional JSONL file."""

    def __init__(self, persistence_path: Path | None = None) -> None:
        self._store: dict[str, OutboxEntry] = {}
        self._lock = threading.Lock()
        self._path = persistence_path
        if persistence_path is not None:
            self._load(persistence_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def put(self, entry: OutboxEntry) -> None:
        """Insert or replace an outbox entry."""
        with self._lock:
            self._store[entry.event_id] = entry
            self._flush()

    def get(self, event_id: str) -> OutboxEntry | None:
        """Return the entry for *event_id*, or None."""
        with self._lock:
            return self._store.get(event_id)

    def pending(self) -> list[OutboxEntry]:
        """Return all entries with status PENDING."""
        with self._lock:
            return [e for e in self._store.values() if e.status == "PENDING"]

    def mark_published(self, event_id: str) -> None:
        """Transition an entry to PUBLISHED."""
        with self._lock:
            entry = self._store.get(event_id)
            if entry is None:
                raise KeyError(event_id)
            entry.status = "PUBLISHED"
            entry.published_at = datetime.now(tz=UTC).isoformat()
            self._flush()

    def mark_failed(self, event_id: str) -> None:
        """Transition an entry to FAILED and increment retry_count."""
        with self._lock:
            entry = self._store.get(event_id)
            if entry is None:
                raise KeyError(event_id)
            entry.status = "FAILED"
            entry.retry_count += 1
            self._flush()

    def all_entries(self) -> list[OutboxEntry]:
        """Return a snapshot of all entries."""
        with self._lock:
            return list(self._store.values())

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
                    entry = OutboxEntry.from_dict(data)
                    self._store[entry.event_id] = entry
                except (json.JSONDecodeError, KeyError):
                    continue

    def _flush(self) -> None:
        """Rewrite the entire JSONL file (called under lock)."""
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w") as fh:
            for entry in self._store.values():
                fh.write(json.dumps(entry.to_dict()) + "\n")
