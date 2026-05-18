"""Graph algorithms — build, roots/leaves, cycles, topo sort."""

from __future__ import annotations

import pytest

from dbtlin.graph import build_graph, find_cycles, leaves, roots, topological_order
from dbtlin.schema import Model, NodeId, NodeKind


def _m(name: str, refs: tuple[str, ...] = (), sources: tuple[tuple[str, str], ...] = ()) -> Model:
    return Model(name=name, sql="", refs=refs, sources=sources)


def test_build_graph_single_model_no_deps():
    g = build_graph([_m("only_model")])
    assert len(g.nodes) == 1
    assert g.upstream_of == {}


def test_build_graph_adds_model_to_model_edge():
    g = build_graph([_m("downstream", refs=("upstream",))])
    assert NodeId(kind=NodeKind.MODEL, name="upstream") in g.nodes
    assert NodeId(kind=NodeKind.MODEL, name="downstream") in g.nodes
    edge_list = g.edges()
    assert len(edge_list) == 1
    assert edge_list[0].downstream.name == "downstream"
    assert edge_list[0].upstream.name == "upstream"


def test_build_graph_adds_source_edge():
    g = build_graph([_m("stg_orders", sources=(("shopee", "raw_orders"),))])
    source = NodeId(kind=NodeKind.SOURCE, name="shopee.raw_orders")
    assert source in g.nodes
    assert source in g.upstream_of[NodeId(kind=NodeKind.MODEL, name="stg_orders")]


def test_build_graph_idempotent_add_edge():
    """Same edge added twice → still one edge (set-deduplicated)."""
    m = _m("a", refs=("b", "b", "b"))
    g = build_graph([m])
    assert len(g.edges()) == 1


def test_roots_are_nodes_with_no_upstream():
    g = build_graph(
        [
            _m("a", refs=("b",)),  # a depends on b
            _m("b", refs=("c",)),  # b depends on c
            # c has no model — implicit source-like node
        ]
    )
    r = roots(g)
    # c is a root (no upstream).
    assert NodeId(kind=NodeKind.MODEL, name="c") in r


def test_leaves_are_nodes_with_no_downstream():
    g = build_graph(
        [
            _m("a", refs=("b",)),
            _m("b", refs=("c",)),
        ]
    )
    leaves_list = leaves(g)
    # a is a leaf (no downstream).
    assert NodeId(kind=NodeKind.MODEL, name="a") in leaves_list


# ---------- Tarjan SCC -------------------------------------------------


def test_find_cycles_acyclic_returns_empty():
    g = build_graph(
        [
            _m("a", refs=("b",)),
            _m("b", refs=("c",)),
            _m("c"),
        ]
    )
    assert find_cycles(g) == []


def test_find_cycles_detects_two_node_cycle():
    g = build_graph(
        [
            _m("a", refs=("b",)),
            _m("b", refs=("a",)),
        ]
    )
    cycles = find_cycles(g)
    assert len(cycles) == 1
    names = {n.name for n in cycles[0].cycle}
    assert names == {"a", "b"}


def test_find_cycles_detects_three_node_cycle():
    g = build_graph(
        [
            _m("a", refs=("b",)),
            _m("b", refs=("c",)),
            _m("c", refs=("a",)),
        ]
    )
    cycles = find_cycles(g)
    assert len(cycles) == 1
    assert len(cycles[0].cycle) == 3


def test_find_cycles_detects_self_loop():
    g = build_graph([_m("a", refs=("a",))])
    cycles = find_cycles(g)
    assert len(cycles) == 1
    assert cycles[0].cycle == (
        NodeId(kind=NodeKind.MODEL, name="a"),
        NodeId(kind=NodeKind.MODEL, name="a"),
    )


def test_find_cycles_handles_multiple_components():
    """Two independent cycles in disconnected components are both found."""
    g = build_graph(
        [
            _m("a", refs=("b",)),
            _m("b", refs=("a",)),
            _m("c", refs=("d",)),
            _m("d", refs=("c",)),
        ]
    )
    assert len(find_cycles(g)) == 2


# ---------- Kahn topological sort ----------------------------------------


def test_topo_returns_sources_first():
    g = build_graph([_m("downstream", refs=("upstream",))])
    order = topological_order(g)
    upstream_idx = order.index(NodeId(kind=NodeKind.MODEL, name="upstream"))
    downstream_idx = order.index(NodeId(kind=NodeKind.MODEL, name="downstream"))
    assert upstream_idx < downstream_idx


def test_topo_raises_on_cycle():
    g = build_graph(
        [
            _m("a", refs=("b",)),
            _m("b", refs=("a",)),
        ]
    )
    with pytest.raises(ValueError, match="cycle"):
        topological_order(g)


def test_topo_total_over_nodes():
    g = build_graph(
        [
            _m("a", refs=("b",)),
            _m("b", refs=("c",)),
            _m("c"),
        ]
    )
    order = topological_order(g)
    assert len(order) == 3
    assert set(order) == g.nodes


def test_topo_deterministic_ties():
    """Independent nodes resolve in label-alphabetical order."""
    g = build_graph([_m("x"), _m("a"), _m("m")])
    order = topological_order(g)
    labels = [n.label for n in order]
    assert labels == sorted(labels)


def test_topo_sources_before_models():
    """SOURCE nodes come before all MODELs that depend on them."""
    g = build_graph(
        [
            _m("stg", sources=(("s", "t"),)),
        ]
    )
    order = topological_order(g)
    source_idx = order.index(NodeId(kind=NodeKind.SOURCE, name="s.t"))
    model_idx = order.index(NodeId(kind=NodeKind.MODEL, name="stg"))
    assert source_idx < model_idx
