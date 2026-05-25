"""Tests for JSONL I/O."""

from __future__ import annotations

import io
import json

import pytest

from datacatalog.io_jsonl import (
    column_from_dict,
    column_to_dict,
    edge_from_dict,
    edge_to_dict,
    read_edges,
    read_sources,
    source_to_dict,
    write_edges,
    write_sources,
)
from datacatalog.schema import (
    Column,
    ColumnRef,
    DataSource,
    LineageEdge,
    PIICategory,
    Table,
)


def _source() -> DataSource:
    src = DataSource("raw", "Raw DB")
    src.tables = [
        Table(
            "users",
            schema="public",
            columns=[Column("email", "varchar", pii=PIICategory.EMAIL)],
        )
    ]
    return src


def _edge() -> LineageEdge:
    return LineageEdge(
        ColumnRef("raw", "public", "users", "email"),
        ColumnRef("stg", "public", "users_stg", "email"),
        "j1",
    )


class TestColumnSerde:
    def test_roundtrip(self) -> None:
        c = Column("email", "varchar", pii=PIICategory.EMAIL)
        d = column_to_dict(c)
        assert column_from_dict(d) == c

    def test_default_pii_none(self) -> None:
        c = Column("user_id", "int")
        d = column_to_dict(c)
        recovered = column_from_dict(d)
        assert recovered.pii == PIICategory.NONE


class TestSourceSerde:
    def test_roundtrip_jsonl(self) -> None:
        src = _source()
        buf = io.StringIO()
        write_sources([src], buf)
        buf.seek(0)
        result = read_sources(buf)
        assert len(result) == 1
        assert result[0].source_id == "raw"
        assert result[0].tables[0].name == "users"

    def test_empty_file(self) -> None:
        buf = io.StringIO("")
        assert read_sources(buf) == []

    def test_output_is_valid_json(self) -> None:
        src = _source()
        d = source_to_dict(src)
        json.dumps(d)  # no exception


class TestEdgeSerde:
    def test_roundtrip_dict(self) -> None:
        e = _edge()
        assert edge_from_dict(edge_to_dict(e)) == e

    def test_roundtrip_jsonl(self) -> None:
        edges = [_edge()]
        buf = io.StringIO()
        write_edges(edges, buf)
        buf.seek(0)
        result = read_edges(buf)
        assert result == edges

    def test_invalid_ref_format(self) -> None:
        with pytest.raises(ValueError):
            edge_from_dict({"source": "bad.format", "target": "a.b.c.d", "job_id": "j"})
