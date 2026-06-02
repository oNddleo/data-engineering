"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from dbtlin.io_jsonl import (
    dump_edges,
    dump_models,
    load_edges,
    load_models,
    model_from_dict,
    project_from_json,
    project_to_json,
)
from dbtlin.schema import Edge, Model, NodeId, NodeKind


def test_model_roundtrip():
    m = Model(
        name="stg_orders",
        sql="select * from {{ source('s', 't') }}",
        refs=(),
        sources=(("s", "t"),),
        path="models/staging/stg_orders.sql",
    )
    [back] = load_models(dump_models([m]))
    assert back == m


def test_edge_roundtrip():
    e = Edge(
        downstream=NodeId(kind=NodeKind.MODEL, name="a"),
        upstream=NodeId(kind=NodeKind.MODEL, name="b"),
    )
    [back] = load_edges(dump_edges([e]))
    assert back == e


def test_project_roundtrip():
    project = {
        "model_a": "select 1",
        "model_b": "select * from {{ ref('model_a') }}",
    }
    back = project_from_json(project_to_json(project))
    assert back == project


def test_project_emits_sorted_keys():
    project = {"z": "1", "a": "2", "m": "3"}
    text = project_to_json(project)
    a_pos = text.index('"a"')
    m_pos = text.index('"m"')
    z_pos = text.index('"z"')
    assert a_pos < m_pos < z_pos


def test_model_decoder_rejects_bad_sources():
    bad = {
        "name": "x",
        "sql": "select 1",
        "refs": [],
        "sources": [["only_one_element"]],
        "path": "",
    }
    with pytest.raises(TypeError, match="source"):
        model_from_dict(bad)


def test_project_decoder_rejects_non_object():
    with pytest.raises(TypeError):
        project_from_json('["not", "an object"]')


def test_project_decoder_rejects_missing_models():
    with pytest.raises(TypeError, match="models"):
        project_from_json('{"other_key": {}}')


def test_project_decoder_rejects_non_string_values():
    with pytest.raises(TypeError):
        project_from_json('{"models": {"x": 42}}')


def test_blank_lines_skipped():
    text = dump_models([Model(name="x", sql="select 1")])
    padded = "\n\n" + text + "\n\n"
    assert len(load_models(padded)) == 1
