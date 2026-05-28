"""AuditLog: append ValidationRun entries (JSONL on disk); query history."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class ValidationRun:
    """A single audit record written after each batch is processed."""

    run_id: str
    suite_name: str
    timestamp: str  # ISO-8601 UTC
    pass_rate: float
    total: int
    failed: int
    gate_status: str  # "open" or "blocked"

    def to_dict(self) -> dict[str, object]:
        return dict(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ValidationRun:
        return cls(
            run_id=str(data["run_id"]),
            suite_name=str(data["suite_name"]),
            timestamp=str(data["timestamp"]),
            pass_rate=float(data["pass_rate"]),  # type: ignore[arg-type]
            total=int(data["total"]),  # type: ignore[call-overload]
            failed=int(data["failed"]),  # type: ignore[call-overload]
            gate_status=str(data["gate_status"]),
        )

    @staticmethod
    def now_iso() -> str:
        return datetime.now(tz=UTC).isoformat()


class AuditLog:
    """Thread-safe append-only JSONL audit log persisted to *path*.

    Each line is a JSON object representing one :class:`ValidationRun`.

    Parameters
    ----------
    path:
        File path for the JSONL log.  Created (with parent dirs) if absent.
    """

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def append(self, run: ValidationRun) -> None:
        """Append *run* as a JSONL line."""
        line = json.dumps(run.to_dict()) + "\n"
        with self._lock:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(line)

    def query(self, last_n: int = 10) -> list[ValidationRun]:
        """Return the *last_n* most recent runs (oldest-first within that slice)."""
        if not self._path.exists():
            return []
        with self._lock:
            lines = self._path.read_text(encoding="utf-8").splitlines()
        runs: list[ValidationRun] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                data: dict[str, object] = json.loads(line)
                runs.append(ValidationRun.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                continue
        return runs[-last_n:]

    def clear(self) -> None:
        """Delete the log file (used by CLI reset)."""
        with self._lock:
            if self._path.exists():
                self._path.unlink()
