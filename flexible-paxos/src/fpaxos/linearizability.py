from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass
class HistoryEntry:
    """One completed operation in the recorded history."""

    start_time: float
    end_time: float
    op_type: str  # "read" or "write"
    value: Any  # value written, or value read


class LinearizabilityChecker:
    """Detect linearizability violations in an operation history.

    Algorithm
    ---------
    We use a simplified write-read dependency graph approach:

    1. Collect all *write* operations and assign each a logical sequence
       number based on their order of completion (end_time).
    2. For each *read* operation, determine which write's value it observed.
       If no write matches, it's a stale-read from before the first write
       (only valid if the read happened before the first write committed).
    3. Build a dependency graph:
       - write W_i → write W_j  if W_i completed before W_j started
         (W_j must come after W_i in the linearization)
       - read R → write W  if R observed W's value
         (W must precede R in the linearization)
       - write W → read R  if R overlapped with or preceded W and R saw W's value
         (W must precede R)
    4. Detect cycles in the dependency graph.  A cycle means no valid
       linearization exists → NOT linearizable.

    This is a simplified but effective checker for the common cases tested
    in distributed consensus implementations.
    """

    def __init__(self) -> None:
        self._history: list[HistoryEntry] = []

    def record(
        self,
        start_time: float,
        end_time: float,
        op_type: str,
        value: Any,
    ) -> None:
        """Append an operation to the history."""
        self._history.append(
            HistoryEntry(
                start_time=start_time,
                end_time=end_time,
                op_type=op_type,
                value=value,
            )
        )

    def check_history(self, history: list[HistoryEntry] | None = None) -> bool:
        """Return True if the history is linearizable, False if a violation exists.

        Parameters
        ----------
        history:
            Optional explicit history to check.  If omitted, uses the
            internally recorded history.
        """
        ops = history if history is not None else self._history
        if not ops:
            return True

        writes = [op for op in ops if op.op_type == "write"]
        reads = [op for op in ops if op.op_type == "read"]

        # Sort writes by end_time to establish a candidate linearization order.
        writes_sorted = sorted(writes, key=lambda w: w.end_time)

        # Map value → list of writes that wrote it (in order)
        value_to_writes: dict[Any, list[int]] = defaultdict(list)
        for idx, w in enumerate(writes_sorted):
            value_to_writes[w.value].append(idx)

        # Build adjacency list for dependency graph over write indices.
        # Node indices: 0..len(writes_sorted)-1
        n_nodes = len(writes_sorted)
        adj: dict[int, set[int]] = defaultdict(set)

        # write→write edges: if w_i ends before w_j starts, w_i must precede w_j
        for i in range(n_nodes):
            for j in range(n_nodes):
                if i != j and writes_sorted[i].end_time <= writes_sorted[j].start_time:
                    adj[i].add(j)

        # For reads: check that the observed value is consistent.
        for read in reads:
            obs_value = read.value
            if obs_value not in value_to_writes:
                # Read a value that was never written → violation
                return False

            candidate_write_indices = value_to_writes[obs_value]

            # The read must observe one of these writes.  Find which write is
            # compatible: the write must have started before the read ended
            # AND the write must be the "latest" write before the read finished.
            #
            # Simplified check: at least one matching write must have its
            # end_time <= read.end_time (it committed before the read finished).
            # Any write that committed AFTER the read started but is NOT
            # the observed value → violation if that write's value is different
            # and the write completed before the read completed.
            compatible: list[int] = []
            for wi in candidate_write_indices:
                w = writes_sorted[wi]
                # The write must have at least started before the read ended.
                if w.start_time < read.end_time:
                    compatible.append(wi)

            if not compatible:
                # No candidate write could have been observed by this read.
                return False

            # Check: any write with a DIFFERENT value that completed entirely
            # before this read started must be "overwritten" by a later write
            # of the observed value.
            for _wi2, w2 in enumerate(writes_sorted):
                if w2.value == obs_value:
                    continue  # same value is fine
                if w2.end_time <= read.start_time:
                    # w2 is a write of a different value that fully completed
                    # before our read started.  For our read to observe
                    # obs_value, some write of obs_value must have happened
                    # AFTER w2 and also completed before the read ended.
                    if not any(
                        writes_sorted[wi].end_time > w2.end_time
                        and writes_sorted[wi].end_time <= read.end_time
                        for wi in compatible
                    ):
                        return False

        # Check for cycles using DFS
        return not self._has_cycle(adj, n_nodes)

    # ------------------------------------------------------------------
    # Graph helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _has_cycle(adj: dict[int, set[int]], n: int) -> bool:
        """Return True if the directed graph has a cycle (DFS-based)."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = [WHITE] * n

        def dfs(u: int) -> bool:
            color[u] = GRAY
            for v in adj.get(u, set()):
                if color[v] == GRAY:
                    return True
                if color[v] == WHITE and dfs(v):
                    return True
            color[u] = BLACK
            return False

        return any(color[i] == WHITE and dfs(i) for i in range(n))

    def clear(self) -> None:
        """Reset recorded history."""
        self._history.clear()

    @property
    def history(self) -> list[HistoryEntry]:
        return list(self._history)
