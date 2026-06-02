"""RecoveryAgent: scans stuck sagas and triggers compensation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from .coordinator import SagaState, TransactionCoordinator

if TYPE_CHECKING:
    from .dlq import DeadLetterQueue

# States that are considered "terminal" (no recovery needed)
_TERMINAL_STATES = {
    SagaState.COMPLETED,
    SagaState.COMPENSATED,
    SagaState.FAILED,
}

# States that are actively "in-progress" and may get stuck
_STUCK_STATES = {
    SagaState.PENDING,
    SagaState.KAFKA_PUBLISHED,
    SagaState.WAREHOUSE_ACK,
    SagaState.NOTIFICATION_ACK,
}


class RecoveryAgent:
    """Scans coordinator for stuck sagas and initiates compensation."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(
        self,
        coordinator: TransactionCoordinator,
        timeout_seconds: float = 60.0,
    ) -> list[str]:
        """
        Return the saga_ids of sagas that are stuck (in a non-terminal,
        non-compensating state for longer than *timeout_seconds*).
        """
        now = datetime.now(tz=UTC)
        stuck: list[str] = []

        for saga in coordinator.all_sagas():
            if saga.state not in _STUCK_STATES:
                continue
            try:
                updated = datetime.fromisoformat(saga.updated_at)
                # Make aware if naive
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=UTC)
                elapsed = (now - updated).total_seconds()
                if elapsed >= timeout_seconds:
                    stuck.append(saga.saga_id)
            except (ValueError, AttributeError):
                # If we can't parse the timestamp treat as stuck
                stuck.append(saga.saga_id)

        return stuck

    def recover(
        self,
        saga_id: str,
        coordinator: TransactionCoordinator,
        dlq: DeadLetterQueue,
    ) -> None:
        """
        Attempt recovery of *saga_id*:
        - Move the saga to COMPENSATING state.
        - Enqueue the original event to the DLQ for manual/automated replay.
        """
        saga = coordinator.get(saga_id)
        if saga is None:
            raise KeyError(f"Unknown saga: {saga_id}")

        if saga.state in _TERMINAL_STATES:
            return  # Nothing to do

        coordinator.compensate(saga_id)

        dlq.enqueue(
            event=dict(saga.payload),
            reason=f"Recovery: saga stuck in {saga.state.value}",
            source_consumer="RecoveryAgent",
        )
