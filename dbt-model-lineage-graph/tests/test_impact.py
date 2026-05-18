"""Upstream / downstream impact analysis."""

from __future__ import annotations

import pytest

from dbtlin.graph import build_graph
from dbtlin.impact import downstream_of, impact, impact_by_name, upstream_of
from dbtlin.schema import Model, NodeId, NodeKind


def _m(name: str, refs: tuple[str, ...] = ()) -> Model:
    return Model(name=name, sql="", refs=refs)


def test_upstream_chain_climbs_recursively():
    g = build_graph(
        [
            _m("a", refs=("b",)),
            _m("b", refs=("c",)),
            _m("c"),
        ]
    )
    out = upstream_of(g, NodeId(kind=NodeKind.MODEL, name="a"))
    names = {n.name for n in out}
    assert names == {"b", "c"}


def test_downstream_chain_walks_dependents():
    g = build_graph(
        [
            _m("a", refs=("b",)),
            _m("aa", refs=("b",)),
            _m("b", refs=("c",)),
        ]
    )
    out = downstream_of(g, NodeId(kind=NodeKind.MODEL, name="b"))
    names = {n.name for n in out}
    assert names == {"a", "aa"}


def test_upstream_excludes_target_itself():
    g = build_graph([_m("a", refs=("b",))])
    out = upstream_of(g, NodeId(kind=NodeKind.MODEL, name="a"))
    assert NodeId(kind=NodeKind.MODEL, name="a") not in out


def test_downstream_excludes_target_itself():
    g = build_graph([_m("a", refs=("b",))])
    out = downstream_of(g, NodeId(kind=NodeKind.MODEL, name="b"))
    assert NodeId(kind=NodeKind.MODEL, name="b") not in out


def test_impact_combines_both_directions():
    g = build_graph(
        [
            _m("a", refs=("b",)),
            _m("b", refs=("c",)),
            _m("c"),
        ]
    )
    r = impact(g, NodeId(kind=NodeKind.MODEL, name="b"))
    upstream_names = {n.name for n in r.upstream}
    downstream_names = {n.name for n in r.downstream}
    assert upstream_names == {"c"}
    assert downstream_names == {"a"}
    assert r.n_total_affected == 2


def test_impact_raises_for_unknown_target():
    g = build_graph([_m("a")])
    with pytest.raises(KeyError):
        impact(g, NodeId(kind=NodeKind.MODEL, name="ghost"))


def test_impact_by_name_convenience():
    g = build_graph([_m("a", refs=("b",))])
    r = impact_by_name(g, "a")
    assert r.target.kind is NodeKind.MODEL
    assert r.target.name == "a"


def test_impact_on_isolated_model():
    """A model with no edges has zero upstream + zero downstream."""
    g = build_graph([_m("isolated")])
    r = impact(g, NodeId(kind=NodeKind.MODEL, name="isolated"))
    assert r.upstream == ()
    assert r.downstream == ()
    assert r.n_total_affected == 0


def test_impact_diamond_pattern():
    """A diamond: a → b → d, a → c → d. Impact of a includes all three others."""
    g = build_graph(
        [
            _m("b", refs=("a",)),
            _m("c", refs=("a",)),
            _m("d", refs=("b", "c")),
        ]
    )
    r = impact_by_name(g, "a")
    downstream_names = {n.name for n in r.downstream}
    assert downstream_names == {"b", "c", "d"}
