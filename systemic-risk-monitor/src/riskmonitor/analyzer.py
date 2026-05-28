"""RiskAnalyzer: orchestrates all risk algorithms and produces a RiskReport."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from riskmonitor.algorithms import (
    CascadeResult,
    Cycle,
    betweenness_centrality,
    cascade_bfs,
    find_cycles,
    gini,
    hhi,
    outbound_vector,
    pagerank,
)

if TYPE_CHECKING:
    from riskmonitor.graph import ExposureGraph


@dataclass
class RiskReport:
    """Aggregated risk metrics for an interbank exposure graph."""

    # Cycle risk
    cycles: list[Cycle] = field(default_factory=list)

    # Centrality
    betweenness: dict[str, float] = field(default_factory=dict)
    pagerank: dict[str, float] = field(default_factory=dict)

    # Concentration
    hhi: float = 0.0
    gini: float = 0.0

    # Cascade simulation
    cascade: CascadeResult | None = None

    # Convenience properties -----------------------------------------------

    @property
    def betweenness_max(self) -> float:
        """Maximum betweenness centrality across all nodes."""
        if not self.betweenness:
            return 0.0
        return max(self.betweenness.values())

    @property
    def betweenness_max_node(self) -> str:
        """Node with the highest betweenness centrality."""
        if not self.betweenness:
            return ""
        return max(self.betweenness, key=lambda v: self.betweenness[v])

    @property
    def max_cycle_notional(self) -> float:
        """Maximum notional across all detected cycles."""
        if not self.cycles:
            return 0.0
        return max(c.notional for c in self.cycles)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable representation."""
        return {
            "cycles": [
                {
                    "nodes": c.nodes,
                    "notional": c.notional,
                    "bottleneck": c.bottleneck,
                }
                for c in self.cycles
            ],
            "betweenness": self.betweenness,
            "pagerank": self.pagerank,
            "hhi": self.hhi,
            "gini": self.gini,
            "betweenness_max": self.betweenness_max,
            "betweenness_max_node": self.betweenness_max_node,
            "max_cycle_notional": self.max_cycle_notional,
            "cascade": {
                "seed": self.cascade.seed,
                "size": self.cascade.size,
                "reached": self.cascade.reached,
            }
            if self.cascade
            else None,
        }


class RiskAnalyzer:
    """Runs all risk algorithms on an :class:`~riskmonitor.graph.ExposureGraph`.

    Usage::

        graph = ExposureGraph()
        # ... populate graph ...
        report = RiskAnalyzer().analyze(graph)
    """

    def analyze(self, graph: ExposureGraph) -> RiskReport:
        """Analyse *graph* and return a :class:`RiskReport`.

        Steps
        -----
        1. Build the adjacency dict from the graph.
        2. Detect all simple cycles (Johnson's DFS).
        3. Compute betweenness centrality (Brandes).
        4. Compute PageRank (power iteration).
        5. Compute HHI and Gini on outbound exposure.
        6. Simulate cascade from the highest-betweenness node.
        """
        adj = graph.adjacency()
        nodes = graph.nodes()

        # Cycle detection
        cycles = find_cycles(adj)

        # Centrality
        bc = betweenness_centrality(adj)
        pr = pagerank(adj)

        # Concentration (on outbound exposure vector)
        out_vec = outbound_vector(adj, nodes)
        h = hhi(out_vec)
        g = gini(out_vec)

        # Cascade
        cascade: CascadeResult | None = None
        if nodes:
            seed_node = max(bc, key=lambda v: bc[v]) if bc else nodes[0]
            cascade = cascade_bfs(adj, seed_node)

        return RiskReport(
            cycles=cycles,
            betweenness=bc,
            pagerank=pr,
            hhi=h,
            gini=g,
            cascade=cascade,
        )
