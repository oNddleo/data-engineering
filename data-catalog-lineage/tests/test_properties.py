"""Hypothesis property tests for data catalog."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from datacatalog.lineage import LineageGraph
from datacatalog.schema import ColumnRef, LineageEdge

_SOURCES = ["raw", "stg", "rep"]
_TABLES = ["t1", "t2", "t3"]
_COLS = ["c1", "c2", "c3"]


def _ref_strategy() -> object:
    return st.builds(
        ColumnRef,
        source_id=st.sampled_from(_SOURCES),
        schema=st.just("public"),
        table=st.sampled_from(_TABLES),
        column=st.sampled_from(_COLS),
    )


class TestLineageProperties:
    @given(
        edges=st.lists(
            st.builds(
                LineageEdge,
                source=_ref_strategy(),
                target=_ref_strategy(),
                job_id=st.just("j1"),
                transform=st.just(""),
            ),
            max_size=10,
        )
    )
    @settings(max_examples=40)
    def test_all_nodes_reachable_from_edges(self, edges: list[LineageEdge]) -> None:
        g = LineageGraph()
        g.add_edges(edges)
        nodes = set(g.nodes())
        for e in edges:
            assert e.source in nodes or e.source == e.target
            assert e.target in nodes or e.source == e.target

    @given(
        a=_ref_strategy(),
        b=_ref_strategy(),
        c=_ref_strategy(),
    )
    @settings(max_examples=30)
    def test_transitive_upstream(self, a: ColumnRef, b: ColumnRef, c: ColumnRef) -> None:
        if a == b or b == c or a == c:
            return
        g = LineageGraph()
        g.add_edges(
            [
                LineageEdge(a, b, "j1"),
                LineageEdge(b, c, "j2"),
            ]
        )
        # a is upstream of c transitively
        ups = g.upstream_of(c)
        assert b in ups
        assert a in ups

    @given(
        edges=st.lists(
            st.builds(
                LineageEdge,
                source=_ref_strategy(),
                target=_ref_strategy(),
                job_id=st.just("j1"),
                transform=st.just(""),
            ),
            max_size=8,
        )
    )
    @settings(max_examples=30)
    def test_idempotent_add(self, edges: list[LineageEdge]) -> None:
        g1 = LineageGraph()
        g1.add_edges(edges)
        g2 = LineageGraph()
        g2.add_edges(edges)
        g2.add_edges(edges)  # add again
        assert len(g1.edges()) == len(g2.edges())

    @given(
        n=st.integers(min_value=2, max_value=6),
    )
    @settings(max_examples=20)
    def test_linear_chain_topological_order(self, n: int) -> None:
        refs = [ColumnRef(f"src{i}", "public", "t", "c") for i in range(n)]
        g = LineageGraph()
        for i in range(n - 1):
            g.add_edge(LineageEdge(refs[i], refs[i + 1], "j"))
        order = g.topological_sort()
        for i in range(n - 1):
            assert order.index(refs[i]) < order.index(refs[i + 1])
