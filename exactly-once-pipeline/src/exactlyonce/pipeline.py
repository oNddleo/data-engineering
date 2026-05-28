"""ExactlyOncePipeline: ties outbox + coordinator + idempotency together."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from exactlyonce.coordinator import SagaState, TransactionCoordinator
from exactlyonce.idempotency import IdempotencyLog
from exactlyonce.outbox import OutboxEntry, OutboxStore


@dataclass
class SagaResult:
    """Result returned by :meth:`ExactlyOncePipeline.process`."""

    saga_id: str | None
    status: SagaState
    skipped_duplicate: bool


class ExactlyOncePipeline:
    """
    High-level pipeline that enforces exactly-once processing semantics.

    Processing steps
    ----------------
    1. Check idempotency — skip if the event has been seen before.
    2. Write the event to the outbox (PENDING).
    3. "Publish" — mark the outbox entry as PUBLISHED.
    4. Advance the coordinator through each saga step.
    5. Mark the saga COMPLETED.
    """

    STEPS = ("kafka_publish", "warehouse_ack", "notification_ack", "complete")

    def __init__(
        self,
        idempotency_log: IdempotencyLog | None = None,
        outbox: OutboxStore | None = None,
        coordinator: TransactionCoordinator | None = None,
        consumer_name: str = "default",
    ) -> None:
        self._idempotency = idempotency_log or IdempotencyLog()
        self._outbox = outbox or OutboxStore()
        self._coordinator = coordinator or TransactionCoordinator()
        self._consumer_name = consumer_name

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, event: dict[str, object]) -> SagaResult:
        """
        Process *event* exactly once.

        The event must contain an ``event_id`` key (str).  If not present,
        a new UUID will be generated and inserted into the event dict.
        """
        event_id = str(event.setdefault("event_id", str(uuid.uuid4())))

        # Step 1 — idempotency check
        if self._idempotency.has_seen(event_id):
            return SagaResult(
                saga_id=None,
                status=SagaState.COMPLETED,
                skipped_duplicate=True,
            )

        # Step 2 — write outbox entry (PENDING)
        entry = OutboxEntry(event_id=event_id, payload=dict(event))
        self._outbox.put(entry)

        # Step 3 — "publish" (mark outbox PUBLISHED)
        self._outbox.mark_published(event_id)

        # Step 4 — begin saga and advance through all steps
        saga_id = self._coordinator.begin(event_id=event_id, payload=dict(event))
        for step in self.STEPS:
            self._coordinator.advance(saga_id, step)

        # Step 5 — mark as seen in idempotency log
        self._idempotency.mark_seen(event_id, self._consumer_name)

        saga = self._coordinator.get(saga_id)
        final_state = saga.state if saga is not None else SagaState.COMPLETED
        return SagaResult(
            saga_id=saga_id,
            status=final_state,
            skipped_duplicate=False,
        )
