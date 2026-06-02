"""IdempotencyLog: in-memory + JSONL-backed deduplication store."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class IdempotencyLog:
    """Thread-safe deduplication log backed by an in-memory set and optional JSONL file."""

    def __init__(self, persistence_path: Path | None = None) -> None:
        self._seen: dict[str, dict[str, str]] = {}
        self._lock = threading.Lock()
        self._path = persistence_path
        if persistence_path is not None:
            self._load(persistence_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def has_seen(self, event_id: str) -> bool:
        """Return True if *event_id* has been processed before."""
        with self._lock:
            return event_id in self._seen

    def mark_seen(
        self,
        event_id: str,
        consumer_name: str,
        ts: datetime | None = None,
    ) -> None:
        """Record *event_id* as processed by *consumer_name*."""
        timestamp = (ts or datetime.now(tz=UTC)).isoformat()
        with self._lock:
            if event_id in self._seen:
                return
            record = {
                "event_id": event_id,
                "consumer": consumer_name,
                "ts": timestamp,
            }
            self._seen[event_id] = record
            if self._path is not None:
                self._append(record)

    def all_entries(self) -> list[dict[str, str]]:
        """Return a snapshot of all recorded entries."""
        with self._lock:
            return list(self._seen.values())

    def count(self) -> int:
        """Return the total number of seen events."""
        with self._lock:
            return len(self._seen)

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
                    record: dict[str, str] = json.loads(line)
                    eid = record["event_id"]
                    if eid not in self._seen:
                        self._seen[eid] = record
                except (json.JSONDecodeError, KeyError):
                    continue

    def _append(self, record: dict[str, str]) -> None:
        assert self._path is not None
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a") as fh:
            fh.write(json.dumps(record) + "\n")
