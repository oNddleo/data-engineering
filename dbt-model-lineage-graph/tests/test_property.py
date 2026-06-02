"""Hypothesis properties — graph invariants."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from dbtlin.graph import build_graph, find_cycles, leaves, roots, topological_order
from dbtlin.impact import downstream_of, upstream_of
from dbtlin.schema import Model, NodeId, NodeKind


@st.composite
def _models(draw: st.DrawFn) -> list[Model]:
    """Random DAG (no cycles) by construction: model_i can ref only model_j<i."""
    n = draw(st.integers(min_value=1, max_value=8))
    out: list[Model] = []
    for i in range(n):
        if i == 0:
            refs: tuple[str, ...] = ()
        else:
            n_refs = draw(st.integers(min_value=0, max_value=min(i, 3)))
            ref_indices = sorted(
                set(
                    draw(
                        st.lists(
                            st.integers(min_value=0, max_value=i - 1),
                            min_size=n_refs,
                            max_size=n_refs,
                        )
                    )
                )
            )
            refs = tuple(f"m{j}" for j in ref_indices)
        out.append(Model(name=f"m{i}", sql="", refs=refs))
    return out


@given(models=_models())
@settings(max_examples=80)
def test_acyclic_models_yield_no_cycles(models: list[Model]) -> None:
    """Lower-index-only refs construct an acyclic DAG by definition."""
    graph = build_graph(models)
    assert find_cycles(graph) == []


@given(models=_models())
@settings(max_examples=80)
def test_topo_sort_total_over_nodes(models: list[Model]) -> None:
    """For acyclic graphs, topological order includes every node exactly once."""
    graph = build_graph(models)
    order = topological_order(graph)
    assert len(order) == len(graph.nodes)
    assert set(order) == graph.nodes


@given(models=_models())
@settings(max_examples=80)
def test_topo_sort_respects_edges(models: list[Model]) -> None:
    """For every edge ``downstream → upstream``, upstream comes first in topo order."""
    graph = build_graph(models)
    order = topological_order(graph)
    pos = {n: i for i, n in enumerate(order)}
    for d, ups in graph.upstream_of.items():
        for u in ups:
            assert pos[u] < pos[d]


@given(models=_models())
@settings(max_examples=80)
def test_roots_and_leaves_are_disjoint_when_more_than_one_node(
    models: list[Model],
) -> None:
    """In a multi-node DAG with edges, a node can't be both root and leaf
    unless it's isolated (no edges at all)."""
    graph = build_graph(models)
    rs = set(roots(graph))
    ls = set(leaves(graph))
    for n in rs & ls:
        # Isolated node — no edges in either direction.
        assert not graph.upstream_of.get(n)
        assert not graph.downstream_of.get(n)


@given(models=_models())
@settings(max_examples=50)
def test_upstream_subset_of_topo_predecessors(models: list[Model]) -> None:
    """upstream_of(x) is a subset of nodes that appear before x in topo order."""
    graph = build_graph(models)
    order = topological_order(graph)
    pos = {n: i for i, n in enumerate(order)}
    for n in graph.nodes:
        ups = set(upstream_of(graph, n))
        for u in ups:
            assert pos[u] < pos[n]


@given(models=_models())
@settings(max_examples=50)
def test_downstream_subset_of_topo_successors(models: list[Model]) -> None:
    """downstream_of(x) is a subset of nodes that appear after x in topo order."""
    graph = build_graph(models)
    order = topological_order(graph)
    pos = {n: i for i, n in enumerate(order)}
    for n in graph.nodes:
        downs = set(downstream_of(graph, n))
        for d in downs:
            assert pos[d] > pos[n]


@given(model_id=st.integers(min_value=0, max_value=5))
@settings(max_examples=10)
def test_self_loop_creates_cycle(model_id: int) -> None:
    """A model that refs itself produces a detected cycle."""
    name = f"m{model_id}"
    graph = build_graph([Model(name=name, sql="", refs=(name,))])
    cycles = find_cycles(graph)
    assert len(cycles) == 1
    assert cycles[0].cycle == (
        NodeId(kind=NodeKind.MODEL, name=name),
        NodeId(kind=NodeKind.MODEL, name=name),
    )
