"""Iterative PageRank on a small directed graph.

Each iteration of the loop bumps the timestamp's iteration component.
Convergence stops the loop and emits to the `converged` sink.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from timely.graph.builder import GraphBuilder

if TYPE_CHECKING:
    from timely.graph.operator import EmitFn
from timely.graph.runtime import Runtime
from timely.timestamp.ts import Timestamp


def pagerank(
    edges: dict[int, list[int]],
    n_nodes: int,
    damping: float = 0.85,
    tol: float = 1e-4,
    max_iter: int = 100,
) -> tuple[list[float], int]:
    """Returns (final_ranks, iterations_to_converge)."""
    g = GraphBuilder()

    # State lives outside the graph; the loop body mutates it.
    state = {
        "ranks": [1.0 / n_nodes] * n_nodes,
        "iter": 0,
    }

    def loop_body(ts: Timestamp, _value: object, emit: EmitFn) -> None:
        prev: list[float] = state["ranks"]  # type: ignore[assignment]
        new = [(1 - damping) / n_nodes] * n_nodes
        for u, neigh in edges.items():
            if not neigh:
                continue
            share = damping * prev[u] / len(neigh)
            for v in neigh:
                new[v] += share
        state["ranks"] = new
        state["iter"] = state["iter"] + 1  # type: ignore[operator]
        diff = sum(abs(a - b) for a, b in zip(prev, new, strict=False))
        if diff < tol or state["iter"] >= max_iter:  # type: ignore[operator]
            emit("converged", ts, tuple(new))
        else:
            emit("loop", ts, None)

    g.iterate("loop", loop_body, input="seed")
    g.source("seed", [(Timestamp(0, 0), None)], downstream="loop")
    g.sink("converged", input="loop")

    rt = Runtime(g)
    rt.run()
    final_ts, final_ranks = g.sinks["converged"][0]
    return list(final_ranks), final_ts.iteration


__all__ = ["pagerank"]
