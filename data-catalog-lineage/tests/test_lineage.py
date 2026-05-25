"""Tests for the lineage graph."""

from __future__ import annotations

from datacatalog.lineage import LineageGraph
from datacatalog.schema import ColumnRef, LineageEdge


def ref(sid: str, tbl: str, col: str) -> ColumnRef:
    return ColumnRef(sid, "public", tbl, col)


def edge(s: ColumnRef, t: ColumnRef, job: str = "j1") -> LineageEdge:
    return LineageEdge(s, t, job)


class TestLineageGraph:
    def test_add_and_get_edges(self) -> None:
        g = LineageGraph()
        e = edge(ref("raw", "t1", "c1"), ref("stg", "t2", "c2"))
        g.add_edge(e)
        assert len(g.edges()) == 1

    def test_idempotent_add(self) -> None:
        g = LineageGraph()
        e = edge(ref("raw", "t1", "c1"), ref("stg", "t2", "c2"))
        g.add_edge(e)
        g.add_edge(e)
        assert len(g.edges()) == 1

    def test_upstream(self) -> None:
        g = LineageGraph()
        r = ref("raw", "t1", "c1")
        s = ref("stg", "t2", "c2")
        p = ref("rep", "t3", "c3")
        g.add_edges([edge(r, s), edge(s, p)])
        ups = g.upstream_of(p)
        assert s in ups
        assert r in ups

    def test_downstream(self) -> None:
        g = LineageGraph()
        r = ref("raw", "t1", "c1")
        s = ref("stg", "t2", "c2")
        p = ref("rep", "t3", "c3")
        g.add_edges([edge(r, s), edge(s, p)])
        downs = g.downstream_of(r)
        assert s in downs
        assert p in downs

    def test_no_cycles_in_topological_sort(self) -> None:
        g = LineageGraph()
        r = ref("raw", "t1", "c1")
        s = ref("stg", "t2", "c2")
        p = ref("rep", "t3", "c3")
        g.add_edges([edge(r, s), edge(s, p)])
        order = g.topological_sort()
        assert order.index(r) < order.index(s)
        assert order.index(s) < order.index(p)

    def test_edges_from(self) -> None:
        g = LineageGraph()
        r = ref("raw", "t1", "c1")
        s = ref("stg", "t2", "c2")
        e = edge(r, s)
        g.add_edge(e)
        assert g.edges_from(r) == [e]

    def test_edges_to(self) -> None:
        g = LineageGraph()
        r = ref("raw", "t1", "c1")
        s = ref("stg", "t2", "c2")
        e = edge(r, s)
        g.add_edge(e)
        assert g.edges_to(s) == [e]

    def test_nodes(self) -> None:
        g = LineageGraph()
        r = ref("raw", "t1", "c1")
        s = ref("stg", "t2", "c2")
        g.add_edge(edge(r, s))
        assert r in g.nodes()
        assert s in g.nodes()

    def test_pii_impact(self) -> None:
        g = LineageGraph()
        pii_col = ref("raw", "customers", "email")
        stg_col = ref("stg", "customers", "email")
        rep_col = ref("rep", "report", "email")
        g.add_edges([edge(pii_col, stg_col), edge(stg_col, rep_col)])
        impacted = g.pii_impact([pii_col])
        assert stg_col in impacted
        assert rep_col in impacted

    def test_edges_for_table(self) -> None:
        g = LineageGraph()
        r = ref("raw", "customers", "email")
        s = ref("stg", "customers", "email")
        g.add_edge(edge(r, s))
        result = g.edges_for_table("raw", "public", "customers")
        assert len(result) == 1

    def test_upstream_empty(self) -> None:
        g = LineageGraph()
        r = ref("raw", "t1", "c1")
        assert g.upstream_of(r) == []
