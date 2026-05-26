"""
Abstract base class every pipeline version must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BasePipeline(ABC):
    """
    Minimal contract for a versioned data pipeline.

    A pipeline is a stateful, record-by-record processor.  Each call to
    ``process`` may read and update internal state (e.g. running aggregates,
    ML model context, lookup caches).

    Implementations must be thread-safe if the shadow runner is used with
    concurrent record dispatch.
    """

    @property
    @abstractmethod
    def version(self) -> str:
        """Human-readable version tag, e.g. ``'v1'`` or ``'v2.3.1'``."""

    @abstractmethod
    def process(self, record: dict[str, Any]) -> dict[str, Any]:
        """
        Process a single record and return the pipeline's output.

        Args:
            record: Arbitrary key/value input record.

        Returns:
            Arbitrary key/value output record.  The shadow runner will diff
            this against the other version's output.
        """

    def setup(self) -> None:  # noqa: B027
        """
        Called once before any records are processed.
        Override to open connections, load models, warm caches, etc.
        """

    def teardown(self) -> None:  # noqa: B027
        """
        Called once after processing is complete.
        Override to flush state, close connections, etc.
        """

    def snapshot_state(self) -> dict[str, Any]:
        """
        Return a serialisable snapshot of internal state.
        Used by the orchestrator for checkpointing before traffic shifts.
        Override if the pipeline carries meaningful state.
        """
        return {}

    def restore_state(self, snapshot: dict[str, Any]) -> None:  # noqa: B027
        """
        Restore internal state from a snapshot produced by ``snapshot_state``.
        """
