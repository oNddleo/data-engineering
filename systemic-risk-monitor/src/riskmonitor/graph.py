"""ExposureGraph: directed weighted graph for interbank net bilateral exposures."""

from __future__ import annotations

from collections import defaultdict


class ExposureGraph:
    """Directed weighted graph tracking net bilateral interbank exposures.

    Internally stores gross flows: _flows[a][b] = total amount transferred a→b.
    net_exposure(a, b) = _flows[a][b] - _flows[b][a].
    """

    def __init__(self) -> None:
        # _flows[from][to] = cumulative gross transfer amount
        self._flows: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._node_set: set[str] = set()

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_transfer(self, from_id: str, to_id: str, amount: float) -> None:
        """Accumulate a transfer of *amount* from *from_id* to *to_id*.

        Both nodes are registered even if amount is 0.
        """
        if amount < 0:
            raise ValueError(f"Transfer amount must be non-negative, got {amount!r}")
        self._node_set.add(from_id)
        self._node_set.add(to_id)
        self._flows[from_id][to_id] += amount

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def net_exposure(self, a: str, b: str) -> float:
        """Return net exposure of *a* to *b*: positive means *a* is net creditor.

        Net = gross(a→b) − gross(b→a).
        """
        return self._flows.get(a, {}).get(b, 0.0) - self._flows.get(b, {}).get(a, 0.0)

    def nodes(self) -> list[str]:
        """Return sorted list of all node identifiers."""
        return sorted(self._node_set)

    def edges(self) -> list[tuple[str, str, float]]:
        """Return list of (from, to, net_weight) for all directed pairs where net>0.

        Only pairs where net_exposure(a, b) > 0 are included to avoid double-counting.
        """
        result: list[tuple[str, str, float]] = []
        for a, targets in list(self._flows.items()):
            for b, gross_ab in list(targets.items()):
                net = gross_ab - self._flows.get(b, {}).get(a, 0.0)
                if net > 0:
                    result.append((a, b, net))
        return sorted(result)

    def total_outbound(self, node: str) -> float:
        """Sum of all positive net outbound exposures from *node*."""
        total = 0.0
        for b in self._node_set:
            net = self.net_exposure(node, b)
            if net > 0:
                total += net
        return total

    def total_inbound(self, node: str) -> float:
        """Sum of all positive net inbound exposures to *node*."""
        total = 0.0
        for a in self._node_set:
            net = self.net_exposure(a, node)
            if net > 0:
                total += net
        return total

    # ------------------------------------------------------------------
    # Graph helpers used by algorithms
    # ------------------------------------------------------------------

    def adjacency(self) -> dict[str, dict[str, float]]:
        """Return adjacency dict {from: {to: net_weight}} for positive-net edges."""
        adj: dict[str, dict[str, float]] = {n: {} for n in self._node_set}
        for a, targets in list(self._flows.items()):
            for b, gross_ab in list(targets.items()):
                net = gross_ab - self._flows.get(b, {}).get(a, 0.0)
                if net > 0:
                    adj[a][b] = net
        return adj

    def __len__(self) -> int:
        return len(self._node_set)

    def __repr__(self) -> str:
        return f"ExposureGraph(nodes={len(self._node_set)}, edges={len(self.edges())})"
