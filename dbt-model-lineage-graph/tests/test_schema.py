"""Schema invariants."""

from __future__ import annotations

import pytest

from dbtlin.schema import CycleReport, Edge, Model, NodeId, NodeKind


def test_node_kind_enum():
    assert {k.value for k in NodeKind} == {"MODEL", "SOURCE"}


def test_node_id_model_label():
    n = NodeId(kind=NodeKind.MODEL, name="stg_orders")
    assert n.label == "MODEL:stg_orders"


def test_node_id_source_label():
    n = NodeId(kind=NodeKind.SOURCE, name="shopee.raw_orders")
    assert n.label == "SOURCE:shopee.raw_orders"


def test_node_id_source_requires_dotted_name():
    with pytest.raises(ValueError, match="schema.table"):
        NodeId(kind=NodeKind.SOURCE, name="just_a_name")


def test_node_id_rejects_empty_name():
    with pytest.raises(ValueError):
        NodeId(kind=NodeKind.MODEL, name="")


def test_model_rejects_empty_name():
    with pytest.raises(ValueError):
        Model(name="", sql="select 1")


def test_model_rejects_path_separator_in_name():
    with pytest.raises(ValueError, match="basename"):
        Model(name="models/stg.sql", sql="select 1")


def test_cycle_report_rejects_short_cycle():
    """A 'cycle' of one node makes no sense — except for a self-loop pair."""
    with pytest.raises(ValueError):
        CycleReport(cycle=(NodeId(kind=NodeKind.MODEL, name="x"),))


def test_cycle_report_accepts_self_loop_pair():
    """Self-loop is represented as (x, x) — two entries."""
    n = NodeId(kind=NodeKind.MODEL, name="x")
    c = CycleReport(cycle=(n, n))
    assert len(c.cycle) == 2


def test_edge_holds_two_nodes():
    a = NodeId(kind=NodeKind.MODEL, name="a")
    b = NodeId(kind=NodeKind.MODEL, name="b")
    e = Edge(downstream=a, upstream=b)
    assert e.downstream == a
    assert e.upstream == b
