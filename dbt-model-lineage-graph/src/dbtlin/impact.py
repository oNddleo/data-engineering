"""Upstream / downstream impact analysis from a target node.

Two BFS traversals over the lineage graph:

* **Upstream impact**: "what does ``X`` depend on, transitively?"
  — climb ``upstream_of`` from ``X``.
* **Downstream impact**: "what depends on ``X``, transitively?"
  — climb ``downstream_of`` from ``X``.

Both exclude the target itself. Each output is sorted by
``NodeId.label`` for stable diffs.

The typical question a data engineer asks:

* Before changing ``raw_orders``: ``downstream_of("raw_orders")`` shows
  every model that breaks if I rename a column.
* Before deprecating ``stg_users``: ``downstream_of`` shows every
  dependent.
* When debugging a wrong number in ``fact_revenue``:
  ``upstream_of("fact_revenue")`` shows every input.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from dbtlin.schema import ImpactReport, NodeId, NodeKind

if TYPE_CHECKING:
    from dbtlin.graph import LineageGraph


def upstream_of(graph: LineageGraph, target: NodeId) -> tuple[NodeId, ...]:
    """BFS up the dependency tree. Excludes ``target``."""
    if target not in graph.nodes:
        raise KeyError(f"target {target.label} not in graph")
    seen: set[NodeId] = {target}
    queue: deque[NodeId] = deque([target])
    out: set[NodeId] = set()
    while queue:
        node = queue.popleft()
        for up in graph.upstream_of.get(node, ()):
            if up in seen:
                continue
            seen.add(up)
            out.add(up)
            queue.append(up)
    return tuple(sorted(out, key=lambda n: n.label))


def downstream_of(graph: LineageGraph, target: NodeId) -> tuple[NodeId, ...]:
    """BFS down the dependency tree. Excludes ``target``."""
    if target not in graph.nodes:
        raise KeyError(f"target {target.label} not in graph")
    seen: set[NodeId] = {target}
    queue: deque[NodeId] = deque([target])
    out: set[NodeId] = set()
    while queue:
        node = queue.popleft()
        for down in graph.downstream_of.get(node, ()):
            if down in seen:
                continue
            seen.add(down)
            out.add(down)
            queue.append(down)
    return tuple(sorted(out, key=lambda n: n.label))


def impact(graph: LineageGraph, target: NodeId) -> ImpactReport:
    """Build an :class:`ImpactReport` for ``target``.

    Raises ``KeyError`` if the target isn't in the graph.
    """
    return ImpactReport(
        target=target,
        upstream=upstream_of(graph, target),
        downstream=downstream_of(graph, target),
    )


def impact_by_name(graph: LineageGraph, model_name: str) -> ImpactReport:
    """Convenience: build impact for a MODEL node by name only."""
    return impact(graph, NodeId(kind=NodeKind.MODEL, name=model_name))


__all__ = ["downstream_of", "impact", "impact_by_name", "upstream_of"]
