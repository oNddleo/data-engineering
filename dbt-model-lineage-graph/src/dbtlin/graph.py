"""Build a directed lineage graph and run the standard analyses.

The graph is held as an adjacency-list:

* ``downstream_of[U] = {V1, V2, …}``  — nodes that depend on U
* ``upstream_of[V] = {U1, U2, …}``    — nodes V depends on

Plus a node set ``nodes``. Edges are deduplicated; multi-edges aren't
meaningful for lineage.

Three algorithms:

* :func:`find_cycles` — Tarjan's SCC algorithm. Returns one
  :class:`CycleReport` per cycle (SCC of size ≥ 2, or a self-loop).
* :func:`topological_order` — Kahn's algorithm. Raises if the graph
  has a cycle; sources come first, leaves last.
* :func:`roots` / :func:`leaves` — nodes with no upstream / no downstream
  respectively. Sources are typically roots; mart-layer models are
  typically leaves.

All outputs are sorted by ``NodeId.label`` for stable diffs.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from dbtlin.schema import CycleReport, Edge, NodeId, NodeKind

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dbtlin.schema import Model


@dataclass(slots=True)
class LineageGraph:
    """Directed graph of model + source dependencies."""

    nodes: set[NodeId] = field(default_factory=set)
    upstream_of: dict[NodeId, set[NodeId]] = field(default_factory=dict)
    downstream_of: dict[NodeId, set[NodeId]] = field(default_factory=dict)

    def add_edge(self, downstream: NodeId, upstream: NodeId) -> None:
        """Record ``downstream → upstream``. Idempotent."""
        if downstream == upstream:
            # Self-edge handling: keep in upstream_of so cycle detection
            # surfaces it as a degenerate cycle.
            self.nodes.add(downstream)
            self.upstream_of.setdefault(downstream, set()).add(upstream)
            self.downstream_of.setdefault(upstream, set()).add(downstream)
            return
        self.nodes.add(downstream)
        self.nodes.add(upstream)
        self.upstream_of.setdefault(downstream, set()).add(upstream)
        self.downstream_of.setdefault(upstream, set()).add(downstream)

    def edges(self) -> list[Edge]:
        """All edges, sorted by ``(downstream.label, upstream.label)``."""
        out: list[Edge] = []
        for d, us in self.upstream_of.items():
            for u in us:
                out.append(Edge(downstream=d, upstream=u))
        out.sort(key=lambda e: (e.downstream.label, e.upstream.label))
        return out


def build_graph(models: Iterable[Model]) -> LineageGraph:
    """Build the lineage graph from parsed models.

    * Each model becomes a MODEL node, even if it has no refs.
    * Each ``source('schema', 'table')`` becomes a SOURCE node.
    * Each ``ref('m')`` adds the edge ``current_model → m``.
    """
    g = LineageGraph()
    for m in models:
        downstream = NodeId(kind=NodeKind.MODEL, name=m.name)
        g.nodes.add(downstream)
        for ref_name in m.refs:
            g.add_edge(downstream, NodeId(kind=NodeKind.MODEL, name=ref_name))
        for schema, table in m.sources:
            g.add_edge(
                downstream,
                NodeId(kind=NodeKind.SOURCE, name=f"{schema}.{table}"),
            )
    return g


def roots(graph: LineageGraph) -> list[NodeId]:
    """Nodes with no upstream dependencies — usually SOURCEs + bootstrap models."""
    out = [n for n in graph.nodes if not graph.upstream_of.get(n)]
    out.sort(key=lambda n: n.label)
    return out


def leaves(graph: LineageGraph) -> list[NodeId]:
    """Nodes with no downstream dependents — usually mart-layer models."""
    out = [n for n in graph.nodes if not graph.downstream_of.get(n)]
    out.sort(key=lambda n: n.label)
    return out


# ---------- Tarjan's SCC for cycle detection -----------------------------


def find_cycles(graph: LineageGraph) -> list[CycleReport]:
    """Find every cycle (SCC of size ≥ 2 or any self-edge) via Tarjan."""
    index_of: dict[NodeId, int] = {}
    lowlink: dict[NodeId, int] = {}
    on_stack: dict[NodeId, bool] = defaultdict(lambda: False)
    stack: list[NodeId] = []
    counter = [0]
    sccs: list[list[NodeId]] = []

    def _strongconnect(v: NodeId) -> None:
        index_of[v] = counter[0]
        lowlink[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack[v] = True
        for w in graph.upstream_of.get(v, ()):
            if w not in index_of:
                _strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack[w]:
                lowlink[v] = min(lowlink[v], index_of[w])
        if lowlink[v] == index_of[v]:
            component: list[NodeId] = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                component.append(w)
                if w == v:
                    break
            sccs.append(component)

    for v in graph.nodes:
        if v not in index_of:
            _strongconnect(v)

    out: list[CycleReport] = []
    for scc in sccs:
        if len(scc) >= 2:
            scc_sorted = tuple(sorted(scc, key=lambda n: n.label))
            out.append(CycleReport(cycle=scc_sorted))
        elif len(scc) == 1:
            v = scc[0]
            if v in graph.upstream_of.get(v, ()):  # self-edge
                out.append(CycleReport(cycle=(v, v)))
    out.sort(key=lambda r: tuple(n.label for n in r.cycle))
    return out


# ---------- Kahn's topological sort --------------------------------------


def topological_order(graph: LineageGraph) -> list[NodeId]:
    """Sources first, leaves last. Raises ``ValueError`` if cycles exist.

    Stable order: ties broken by ``NodeId.label``.
    """
    in_degree: dict[NodeId, int] = {n: 0 for n in graph.nodes}
    for n, ups in graph.upstream_of.items():
        in_degree[n] = len(ups)
    # Kahn iterates "no-incoming-edge" frontier. With our convention
    # (edge points downstream → upstream), no-upstream means a root.
    frontier: deque[NodeId] = deque()
    # Use a sorted insertion so ties resolve deterministically.
    initial = sorted(
        (n for n, d in in_degree.items() if d == 0),
        key=lambda n: n.label,
    )
    frontier.extend(initial)
    out: list[NodeId] = []
    while frontier:
        node = frontier.popleft()
        out.append(node)
        for downstream in sorted(
            graph.downstream_of.get(node, ()),
            key=lambda n: n.label,
        ):
            in_degree[downstream] -= 1
            if in_degree[downstream] == 0:
                frontier.append(downstream)
    if len(out) != len(graph.nodes):
        raise ValueError(
            f"graph has cycles — topological sort impossible "
            f"({len(out)} of {len(graph.nodes)} nodes ordered)"
        )
    return out


__all__ = [
    "LineageGraph",
    "build_graph",
    "find_cycles",
    "leaves",
    "roots",
    "topological_order",
]
