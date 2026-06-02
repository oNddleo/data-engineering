"""QualityGate: in-memory flag per pipeline; block/allow based on pass_rate."""

from __future__ import annotations

import threading


class QualityGate:
    """Thread-safe quality gate that blocks a pipeline when pass_rate is too low.

    Parameters
    ----------
    threshold:
        Minimum pass rate (inclusive) required to keep the gate open.
        Default is 0.95.
    """

    def __init__(self, threshold: float = 0.95) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be in [0.0, 1.0]")
        self._threshold = threshold
        self._blocked = False
        self._lock = threading.Lock()

    @property
    def threshold(self) -> float:
        return self._threshold

    def update(self, pass_rate: float) -> bool:
        """Update gate state and return True if the gate is open (not blocked).

        Parameters
        ----------
        pass_rate:
            The pass rate from the latest ValidationResult, in [0, 1].

        Returns
        -------
        bool
            True  → gate is open (pass_rate >= threshold).
            False → gate is blocked (pass_rate < threshold).
        """
        with self._lock:
            self._blocked = pass_rate < self._threshold
            return not self._blocked

    def is_blocked(self) -> bool:
        """Return True if the gate is currently blocking the pipeline."""
        with self._lock:
            return self._blocked

    def reset(self) -> None:
        """Manually reset the gate to open (unblocked)."""
        with self._lock:
            self._blocked = False
