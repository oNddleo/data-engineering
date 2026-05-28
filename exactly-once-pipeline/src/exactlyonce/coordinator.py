"""TransactionCoordinator: saga state machine for exactly-once processing."""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class SagaState(str, Enum):
    """All possible states for a distributed saga."""

    PENDING = "PENDING"
    KAFKA_PUBLISHED = "KAFKA_PUBLISHED"
    WAREHOUSE_ACK = "WAREHOUSE_ACK"
    NOTIFICATION_ACK = "NOTIFICATION_ACK"
    COMPLETED = "COMPLETED"
    COMPENSATING = "COMPENSATING"
    COMPENSATED = "COMPENSATED"
    FAILED = "FAILED"


# Valid forward transitions
_TRANSITIONS: dict[SagaState, dict[str, SagaState]] = {
    SagaState.PENDING: {
        "kafka_publish": SagaState.KAFKA_PUBLISHED,
    },
    SagaState.KAFKA_PUBLISHED: {
        "warehouse_ack": SagaState.WAREHOUSE_ACK,
    },
    SagaState.WAREHOUSE_ACK: {
        "notification_ack": SagaState.NOTIFICATION_ACK,
    },
    SagaState.NOTIFICATION_ACK: {
        "complete": SagaState.COMPLETED,
    },
    SagaState.COMPENSATING: {
        "compensated": SagaState.COMPENSATED,
    },
}


@dataclass
class SagaRecord:
    """Internal record for a single saga."""

    saga_id: str
    event_id: str
    payload: dict[str, object]
    state: SagaState = SagaState.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["state"] = self.state.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> SagaRecord:
        return cls(
            saga_id=str(data["saga_id"]),
            event_id=str(data["event_id"]),
            payload=dict(data["payload"]),  # type: ignore[call-overload]
            state=SagaState(data["state"]),
            created_at=str(data.get("created_at", datetime.now(tz=UTC).isoformat())),
            updated_at=str(data.get("updated_at", datetime.now(tz=UTC).isoformat())),
            steps=list(data.get("steps", [])),  # type: ignore[call-overload]
        )


class TransactionCoordinator:
    """Thread-safe saga coordinator with optional JSONL persistence."""

    def __init__(self, persistence_path: Path | None = None) -> None:
        self._sagas: dict[str, SagaRecord] = {}
        self._lock = threading.Lock()
        self._path = persistence_path
        if persistence_path is not None:
            self._load(persistence_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def begin(self, event_id: str, payload: dict[str, object]) -> str:
        """Start a new saga and return its *saga_id*."""
        saga_id = str(uuid.uuid4())
        record = SagaRecord(saga_id=saga_id, event_id=event_id, payload=payload)
        with self._lock:
            self._sagas[saga_id] = record
            self._flush()
        return saga_id

    def advance(self, saga_id: str, step: str) -> SagaState:
        """Apply *step* to the saga, returning the new state."""
        with self._lock:
            record = self._sagas.get(saga_id)
            if record is None:
                raise KeyError(f"Unknown saga: {saga_id}")
            transitions = _TRANSITIONS.get(record.state, {})
            new_state = transitions.get(step)
            if new_state is None:
                raise ValueError(f"Invalid transition '{step}' from state {record.state.value}")
            record.state = new_state
            record.updated_at = datetime.now(tz=UTC).isoformat()
            record.steps.append(step)
            self._flush()
            return new_state

    def compensate(self, saga_id: str) -> None:
        """Move a saga into COMPENSATING state."""
        with self._lock:
            record = self._sagas.get(saga_id)
            if record is None:
                raise KeyError(f"Unknown saga: {saga_id}")
            record.state = SagaState.COMPENSATING
            record.updated_at = datetime.now(tz=UTC).isoformat()
            record.steps.append("compensate")
            self._flush()

    def get(self, saga_id: str) -> SagaRecord | None:
        """Return the saga record, or None."""
        with self._lock:
            return self._sagas.get(saga_id)

    def all_sagas(self) -> list[SagaRecord]:
        """Return a snapshot of all saga records."""
        with self._lock:
            return list(self._sagas.values())

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
                    record = SagaRecord.from_dict(data)
                    self._sagas[record.saga_id] = record
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

    def _flush(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w") as fh:
            for record in self._sagas.values():
                fh.write(json.dumps(record.to_dict()) + "\n")
