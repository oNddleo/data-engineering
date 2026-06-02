"""Column-level lineage graph with topological traversal."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datacatalog.schema import ColumnRef, LineageEdge


class LineageGraph:
    """Directed acyclic graph of column-level lineage.

    Nodes are ColumnRef objects.
    Edges are LineageEdge objects (source column → target column).
    """

    def __init__(self) -> None:
        self._edges: list[LineageEdge] = []
        # adjacency: source → list of (edge, target)
        self._downstream: dict[ColumnRef, list[LineageEdge]] = defaultdict(list)
        self._upstream: dict[ColumnRef, list[LineageEdge]] = defaultdict(list)
        self._nodes: set[ColumnRef] = set()

    # ── Mutation ─────────────────────────────────────────────────────────────

    def add_edge(self, edge: LineageEdge) -> None:
        if edge in self._edges:
            return
        self._edges.append(edge)
        self._downstream[edge.source].append(edge)
        self._upstream[edge.target].append(edge)
        self._nodes.add(edge.source)
        self._nodes.add(edge.target)

    def add_edges(self, edges: list[LineageEdge]) -> None:
        for e in edges:
            self.add_edge(e)

    # ── Traversal ─────────────────────────────────────────────────────────────

    def upstream_of(self, node: ColumnRef, max_depth: int = 50) -> list[ColumnRef]:
        """All nodes that flow into ``node`` (transitive)."""
        return self._bfs(node, self._upstream, max_depth)

    def downstream_of(self, node: ColumnRef, max_depth: int = 50) -> list[ColumnRef]:
        """All nodes that ``node`` flows into (transitive)."""
        return self._bfs(node, self._downstream, max_depth)

    def _bfs(
        self,
        start: ColumnRef,
        adj: dict[ColumnRef, list[LineageEdge]],
        max_depth: int,
    ) -> list[ColumnRef]:
        visited: set[ColumnRef] = set()
        queue: deque[tuple[ColumnRef, int]] = deque([(start, 0)])
        result: list[ColumnRef] = []
        while queue:
            node, depth = queue.popleft()
            if node in visited or depth > max_depth:
                continue
            visited.add(node)
            if node != start:
                result.append(node)
            for edge in adj.get(node, []):
                neighbour = edge.source if adj is self._upstream else edge.target
                if neighbour not in visited:
                    queue.append((neighbour, depth + 1))
        return result

    # ── Direct edges ─────────────────────────────────────────────────────────

    def edges_from(self, source: ColumnRef) -> list[LineageEdge]:
        return list(self._downstream.get(source, []))

    def edges_to(self, target: ColumnRef) -> list[LineageEdge]:
        return list(self._upstream.get(target, []))

    # ── Queries ───────────────────────────────────────────────────────────────

    def nodes(self) -> list[ColumnRef]:
        return sorted(self._nodes, key=str)

    def edges(self) -> list[LineageEdge]:
        return list(self._edges)

    def edges_for_table(self, source_id: str, schema: str, table: str) -> list[LineageEdge]:
        """All edges involving any column in the given table."""
        return [
            e
            for e in self._edges
            if (
                e.source.source_id == source_id
                and e.source.schema == schema
                and e.source.table == table
            )
            or (
                e.target.source_id == source_id
                and e.target.schema == schema
                and e.target.table == table
            )
        ]

    def pii_impact(self, pii_nodes: list[ColumnRef]) -> list[ColumnRef]:
        """All columns reachable downstream from any PII column."""
        impacted: set[ColumnRef] = set()
        for node in pii_nodes:
            for ds in self.downstream_of(node):
                impacted.add(ds)
        return sorted(impacted, key=str)

    def topological_sort(self) -> list[ColumnRef]:
        """Return nodes in topological order (sources first)."""
        in_degree: dict[ColumnRef, int] = {n: 0 for n in self._nodes}
        for e in self._edges:
            in_degree[e.target] = in_degree.get(e.target, 0) + 1

        queue: deque[ColumnRef] = deque(n for n, d in in_degree.items() if d == 0)
        order: list[ColumnRef] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for edge in self._downstream.get(node, []):
                t = edge.target
                in_degree[t] -= 1
                if in_degree[t] == 0:
                    queue.append(t)
        return order
