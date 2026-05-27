"""QuarantineStore: track bad records by error type."""

from __future__ import annotations

import json
from datetime import datetime, timezone


class QuarantineStore:
    """In-memory store for records that failed healing.

    Each quarantined entry is a plain ``dict`` that is JSON-serialisable.
    """

    def __init__(self) -> None:
        self._records: list[dict[str, object]] = []

    # ------------------------------------------------------------------

    def add(
        self,
        record: dict[str, object],
        error_type: str,
        error_detail: str,
        run_id: str = "",
    ) -> None:
        """Add *record* to the quarantine store."""
        entry: dict[str, object] = {
            "record": dict(record),
            "error_type": error_type,
            "error_detail": error_detail,
            "run_id": run_id,
            "quarantined_at": datetime.now(timezone.utc).isoformat(),
        }
        self._records.append(entry)

    def count(self) -> int:
        """Return the total number of quarantined records."""
        return len(self._records)

    def count_by_error_type(self) -> dict[str, int]:
        """Return a mapping of error_type → count."""
        result: dict[str, int] = {}
        for entry in self._records:
            etype = str(entry["error_type"])
            result[etype] = result.get(etype, 0) + 1
        return result

    def all_records(self) -> list[dict[str, object]]:
        """Return a shallow copy of all quarantine entries."""
        return list(self._records)

    def export_jsonl(self) -> str:
        """Serialise all entries as newline-delimited JSON."""
        lines = [json.dumps(entry, default=str) for entry in self._records]
        return "\n".join(lines)

    def clear(self) -> None:
        """Remove all entries from the store."""
        self._records.clear()
