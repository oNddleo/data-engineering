"""Exactly-once pipeline primitives — stdlib-only."""

from __future__ import annotations

from .coordinator import SagaState, TransactionCoordinator
from .dlq import DeadLetterQueue, DLQEntry
from .idempotency import IdempotencyLog
from .outbox import OutboxEntry, OutboxStore
from .pipeline import ExactlyOncePipeline, SagaResult
from .recovery import RecoveryAgent

__all__ = [
    "DeadLetterQueue",
    "DLQEntry",
    "ExactlyOncePipeline",
    "IdempotencyLog",
    "OutboxEntry",
    "OutboxStore",
    "RecoveryAgent",
    "SagaResult",
    "SagaState",
    "TransactionCoordinator",
]
