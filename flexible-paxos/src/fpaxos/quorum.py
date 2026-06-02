from __future__ import annotations

import math

from fpaxos.types import QuorumConfig


class QuorumManager:
    """Dynamic quorum adjuster based on observed read/write ratio.

    Strategy
    --------
    - **Write-heavy** (write_ratio > threshold): prefer small Q2 (fast
      writes), large Q1.  Minimum Q2 = ⌈(n+1)/3⌉ so the constraint still
      holds with Q1 = n - Q2 + 1.
    - **Read-heavy** (write_ratio < 1 - threshold): prefer small Q1 (fast
      leader election / reads), large Q2.  Minimum Q1 = ⌈(n+1)/3⌉.
    - **Balanced**: fall back to classic majority quorums.

    The invariant Q1 + Q2 > n is **always** enforced by construction.
    """

    # Fraction threshold above/below which we consider the workload skewed.
    _WRITE_HEAVY_THRESHOLD = 0.70
    _READ_HEAVY_THRESHOLD = 0.30

    def __init__(self, n: int) -> None:
        if n < 1:
            raise ValueError("n must be at least 1")
        self.n = n
        self._writes: int = 0
        self._reads: int = 0

    # ------------------------------------------------------------------
    # Recording operations
    # ------------------------------------------------------------------

    def record_write(self) -> None:
        self._writes += 1

    def record_read(self) -> None:
        self._reads += 1

    # ------------------------------------------------------------------
    # Quorum derivation
    # ------------------------------------------------------------------

    @property
    def write_ratio(self) -> float:
        total = self._writes + self._reads
        if total == 0:
            return 0.5
        return self._writes / total

    def get_config(self) -> QuorumConfig:
        """Return the current best QuorumConfig based on workload profile."""
        ratio = self.write_ratio
        if ratio >= self._WRITE_HEAVY_THRESHOLD:
            return self._write_optimized_config()
        if ratio <= self._READ_HEAVY_THRESHOLD:
            return self._read_optimized_config()
        return self._balanced_config()

    # ------------------------------------------------------------------
    # Config builders
    # ------------------------------------------------------------------

    def _balanced_config(self) -> QuorumConfig:
        majority = self.n // 2 + 1
        return QuorumConfig(n=self.n, q1=majority, q2=majority)

    def _write_optimized_config(self) -> QuorumConfig:
        """Small Q2 (write quorum), large Q1 (election quorum).

        Q2_min = ⌈n/3⌉ + 1  (ensuring Q1 = n - Q2 + 1 satisfies Q1+Q2 > n)
        We use Q2 = max(1, n - majority + 1) but clamp so Q1+Q2 > n.
        """
        # Minimum Q2 such that Q1 = n+1 - Q2 satisfies Q1 >= 1 and Q2 >= 1.
        # Also we want Q2 as small as possible: Q2_min = 1, Q1 = n (all nodes).
        # But let's be a bit more practical: Q2 = ceil(n/3), Q1 = n - Q2 + 1.
        q2 = max(1, math.ceil(self.n / 3))
        q1 = self.n - q2 + 1  # guarantees q1 + q2 = n + 1 > n
        return QuorumConfig(n=self.n, q1=q1, q2=q2)

    def _read_optimized_config(self) -> QuorumConfig:
        """Small Q1 (election quorum), large Q2 (write quorum)."""
        q1 = max(1, math.ceil(self.n / 3))
        q2 = self.n - q1 + 1
        return QuorumConfig(n=self.n, q1=q1, q2=q2)

    # ------------------------------------------------------------------
    # Manual override
    # ------------------------------------------------------------------

    def set_config(self, q1: int, q2: int) -> QuorumConfig:
        """Manually override the quorum sizes (validates constraint)."""
        return QuorumConfig(n=self.n, q1=q1, q2=q2)

    # ------------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------------

    @property
    def total_operations(self) -> int:
        return self._writes + self._reads

    @property
    def write_count(self) -> int:
        return self._writes

    @property
    def read_count(self) -> int:
        return self._reads
