"""Graph algorithms for systemic risk analysis.

Implemented:
- Johnson's algorithm for simple cycle enumeration (DFS-based).
- Brandes betweenness centrality (O(V·E), normalised).
- PageRank with power iteration and dangling-node handling.
- HHI (Herfindahl–Hirschman Index) on outbound exposure shares.
- Gini coefficient on outbound exposure distribution.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field


@dataclass
class Cycle:
    """A simple directed cycle in the exposure graph."""

    nodes: list[str]
    notional: float  # sum of edge weights in the cycle
    bottleneck: float  # minimum edge weight in the cycle


# ---------------------------------------------------------------------------
# Johnson's simple cycle enumeration
# ---------------------------------------------------------------------------


def _johnson_unblock(
    node: str,
    blocked: set[str],
    b_map: dict[str, set[str]],
) -> None:
    """Recursively unblock *node* and all nodes that were blocked because of it."""
    blocked.discard(node)
    for w in list(b_map.get(node, set())):
        b_map[node].discard(w)
        if w in blocked:
            _johnson_unblock(w, blocked, b_map)


def find_cycles(adj: dict[str, dict[str, float]]) -> list[Cycle]:
    """Find all simple directed cycles using Johnson's algorithm.

    Parameters
    ----------
    adj:
        Adjacency dict ``{node: {neighbour: weight}}``.

    Returns
    -------
    list[Cycle]
        Every simple cycle found, with notional and bottleneck computed.
    """
    nodes = sorted(adj.keys())
    n = len(nodes)
    index_of = {v: i for i, v in enumerate(nodes)}
    cycles: list[Cycle] = []

    blocked: set[str] = set()
    b_map: dict[str, set[str]] = {v: set() for v in nodes}
    stack: list[str] = []

    def circuit(v: str, s: str) -> bool:
        found = False
        stack.append(v)
        blocked.add(v)

        for w in sorted(adj.get(v, {}).keys()):
            if index_of.get(w, -1) < index_of[s]:
                continue
            if w == s:
                # Completed a cycle
                cycle_nodes = stack[:]
                edge_weights = []
                for i in range(len(cycle_nodes)):
                    a = cycle_nodes[i]
                    b = cycle_nodes[(i + 1) % len(cycle_nodes)]
                    edge_weights.append(adj[a].get(b, 0.0))
                notional = sum(edge_weights)
                bottleneck = min(edge_weights) if edge_weights else 0.0
                cycles.append(
                    Cycle(nodes=cycle_nodes[:], notional=notional, bottleneck=bottleneck)
                )
                found = True
            elif w not in blocked:
                if circuit(w, s):
                    found = True

        if found:
            _johnson_unblock(v, blocked, b_map)
        else:
            for w in sorted(adj.get(v, {}).keys()):
                if index_of.get(w, -1) < index_of[s]:
                    continue
                b_map[w].add(v)

        stack.pop()
        return found

    for i in range(n):
        s = nodes[i]
        # Only consider subgraph of nodes with index >= i
        blocked.clear()
        for v in nodes:
            b_map[v] = set()
        circuit(s, s)

    return cycles


# ---------------------------------------------------------------------------
# Brandes betweenness centrality
# ---------------------------------------------------------------------------


def betweenness_centrality(adj: dict[str, dict[str, float]]) -> dict[str, float]:
    """Compute normalised betweenness centrality using Brandes' algorithm.

    Normalisation factor: ``(n-1)*(n-2)`` (directed graph, n≥3).
    Returns 0.0 for all nodes when ``n < 3``.
    """
    nodes = sorted(adj.keys())
    n = len(nodes)
    cb: dict[str, float] = {v: 0.0 for v in nodes}

    if n < 3:
        return cb

    for s in nodes:
        # BFS to compute shortest-path counts and predecessors
        stack: list[str] = []
        pred: dict[str, list[str]] = {v: [] for v in nodes}
        sigma: dict[str, float] = {v: 0.0 for v in nodes}
        dist: dict[str, int] = {v: -1 for v in nodes}
        sigma[s] = 1.0
        dist[s] = 0
        queue: deque[str] = deque([s])

        while queue:
            v = queue.popleft()
            stack.append(v)
            for w in adj.get(v, {}):
                if dist[w] < 0:
                    queue.append(w)
                    dist[w] = dist[v] + 1
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)

        # Back-propagation
        delta: dict[str, float] = {v: 0.0 for v in nodes}
        while stack:
            w = stack.pop()
            for v in pred[w]:
                if sigma[w] != 0:
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                cb[w] += delta[w]

    # Normalise
    norm = float((n - 1) * (n - 2))
    return {v: cb[v] / norm for v in nodes}


# ---------------------------------------------------------------------------
# PageRank
# ---------------------------------------------------------------------------


def pagerank(
    adj: dict[str, dict[str, float]],
    damping: float = 0.85,
    iterations: int = 50,
) -> dict[str, float]:
    """Compute PageRank using power iteration with dangling-node correction.

    Parameters
    ----------
    adj:
        Adjacency dict ``{node: {neighbour: weight}}``.  Weights are ignored
        (topology-only PageRank).
    damping:
        Damping factor (default 0.85).
    iterations:
        Number of power iterations (default 50).

    Returns
    -------
    dict[str, float]
        Scores summing to 1.0 (within floating-point tolerance).
    """
    nodes = sorted(adj.keys())
    n = len(nodes)
    if n == 0:
        return {}

    rank: dict[str, float] = {v: 1.0 / n for v in nodes}

    # Build out-degree (topology only)
    out_degree: dict[str, int] = {v: len(adj.get(v, {})) for v in nodes}

    for _ in range(iterations):
        dangling_sum = sum(rank[v] for v in nodes if out_degree[v] == 0)
        new_rank: dict[str, float] = {}
        for v in nodes:
            # Incoming contribution from nodes that link to v
            incoming = sum(
                rank[u] / out_degree[u] for u in nodes if v in adj.get(u, {}) and out_degree[u] > 0
            )
            new_rank[v] = (1.0 - damping) / n + damping * (incoming + dangling_sum / n)
        rank = new_rank

    # Normalise to ensure sum == 1.0
    total = sum(rank.values())
    if total > 0:
        rank = {v: r / total for v, r in rank.items()}
    return rank


# ---------------------------------------------------------------------------
# HHI — Herfindahl–Hirschman Index
# ---------------------------------------------------------------------------


def hhi(values: list[float]) -> float:
    """Compute HHI on a distribution of non-negative values.

    HHI = Σ share_i²  where share_i = v_i / Σv.

    Returns 0.0 for an empty or all-zero list.
    Returns 1.0 when all value is concentrated in a single entry.
    """
    total = sum(values)
    if total == 0.0:
        return 0.0
    return sum((v / total) ** 2 for v in values)


# ---------------------------------------------------------------------------
# Gini coefficient
# ---------------------------------------------------------------------------


def gini(values: list[float]) -> float:
    """Compute Gini coefficient on a distribution of non-negative values.

    Formula: Σ_{i≠j} |x_i − x_j| / (2 · n · (n−1) · mean)

    Returns 0.0 for a uniform distribution, empty list, or single-element list.
    Result is always in [0, 1].
    """
    n = len(values)
    if n <= 1:
        return 0.0
    mean = sum(values) / n
    if mean == 0.0:
        return 0.0
    diff_sum = sum(abs(values[i] - values[j]) for i in range(n) for j in range(n) if i != j)
    return diff_sum / (2 * n * (n - 1) * mean)


# ---------------------------------------------------------------------------
# Cascade size (BFS from a seed node after removing its edges)
# ---------------------------------------------------------------------------


@dataclass
class CascadeResult:
    """Result of a cascade simulation."""

    seed: str
    reached: list[str] = field(default_factory=list)

    @property
    def size(self) -> int:
        """Number of nodes reachable in the cascade (excluding seed)."""
        return len(self.reached)


def cascade_bfs(adj: dict[str, dict[str, float]], seed: str) -> CascadeResult:
    """BFS from *seed* after removing all outbound edges of *seed*.

    Models the propagation of distress if the highest-betweenness node fails.
    """
    result = CascadeResult(seed=seed)
    if seed not in adj:
        return result

    # Build modified adjacency — remove seed's outbound edges
    visited: set[str] = {seed}
    queue: deque[str] = deque()

    # Find nodes directly pointing to seed (inbound) — distress propagates outward from seed
    # We model: if seed defaults, all nodes that depended on seed's outbound flows are stressed.
    # Traverse edges: seed's inbound neighbours propagate the cascade onward.
    # For simplicity: BFS on original graph starting from seed's direct inbound sources,
    # then continue via their outbounds (classic contagion BFS).

    # Simpler model used here: remove seed, BFS on residual graph from each of seed's neighbours.
    for neighbour in sorted(adj.get(seed, {}).keys()):
        if neighbour not in visited:
            visited.add(neighbour)
            queue.append(neighbour)
            result.reached.append(neighbour)

    while queue:
        v = queue.popleft()
        for w in sorted(adj.get(v, {}).keys()):
            if w not in visited and w != seed:
                visited.add(w)
                queue.append(w)
                result.reached.append(w)

    return result


# ---------------------------------------------------------------------------
# Convenience: weighted out-degree vector
# ---------------------------------------------------------------------------


def outbound_vector(adj: dict[str, dict[str, float]], nodes: list[str]) -> list[float]:
    """Return list of total outbound weights for each node (in *nodes* order)."""
    return [sum(adj.get(v, {}).values()) for v in nodes]


def _is_close(a: float, b: float, rel_tol: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=1e-12)
