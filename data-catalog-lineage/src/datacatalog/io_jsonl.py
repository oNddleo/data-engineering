"""JSONL serialisation for catalog assets and lineage edges."""

from __future__ import annotations

import json
from typing import IO

from datacatalog.schema import (
    Column,
    ColumnRef,
    DataSource,
    LineageEdge,
    PIICategory,
    Table,
)

# ── Column ────────────────────────────────────────────────────────────────────


def column_to_dict(c: Column) -> dict[str, object]:
    return {
        "name": c.name,
        "dtype": c.dtype,
        "nullable": c.nullable,
        "pii": c.pii.value,
        "sample_values": c.sample_values,
        "description": c.description,
    }


def column_from_dict(obj: dict[str, object]) -> Column:
    sv_raw = obj.get("sample_values")
    sample_values = [str(v) for v in sv_raw] if isinstance(sv_raw, list) else []
    return Column(
        name=str(obj["name"]),
        dtype=str(obj.get("dtype", "")),
        nullable=bool(obj.get("nullable", True)),
        pii=PIICategory(str(obj.get("pii", "NONE"))),
        sample_values=sample_values,
        description=str(obj.get("description", "")),
    )


# ── Table ─────────────────────────────────────────────────────────────────────


def table_to_dict(t: Table) -> dict[str, object]:
    return {
        "name": t.name,
        "schema": t.schema,
        "source_id": t.source_id,
        "row_count": t.row_count,
        "columns": [column_to_dict(c) for c in t.columns],
        "description": t.description,
        "tags": t.tags,
    }


def table_from_dict(obj: dict[str, object]) -> Table:
    cols_raw = obj.get("columns", [])
    cols = [column_from_dict(c) for c in (cols_raw if isinstance(cols_raw, list) else [])]
    tags_raw = obj.get("tags", [])
    tags = [str(t) for t in (tags_raw if isinstance(tags_raw, list) else [])]
    rc = obj.get("row_count", 0)
    return Table(
        name=str(obj["name"]),
        schema=str(obj.get("schema", "public")),
        source_id=str(obj.get("source_id", "")),
        row_count=int(rc) if isinstance(rc, int) else 0,
        columns=cols,
        description=str(obj.get("description", "")),
        tags=tags,
    )


# ── DataSource ────────────────────────────────────────────────────────────────


def source_to_dict(s: DataSource) -> dict[str, object]:
    return {
        "source_id": s.source_id,
        "name": s.name,
        "db_type": s.db_type,
        "tables": [table_to_dict(t) for t in s.tables],
        "description": s.description,
    }


def source_from_dict(obj: dict[str, object]) -> DataSource:
    tbls_raw = obj.get("tables", [])
    tables = [table_from_dict(t) for t in (tbls_raw if isinstance(tbls_raw, list) else [])]
    return DataSource(
        source_id=str(obj["source_id"]),
        name=str(obj["name"]),
        db_type=str(obj.get("db_type", "sqlite")),
        tables=tables,
        description=str(obj.get("description", "")),
    )


# ── LineageEdge ───────────────────────────────────────────────────────────────


def edge_to_dict(e: LineageEdge) -> dict[str, object]:
    return {
        "source": str(e.source),
        "target": str(e.target),
        "job_id": e.job_id,
        "transform": e.transform,
    }


def _ref_from_str(s: str) -> ColumnRef:
    parts = s.split(".")
    if len(parts) != 4:
        raise ValueError(f"Invalid ColumnRef string: {s!r}")
    return ColumnRef(parts[0], parts[1], parts[2], parts[3])


def edge_from_dict(obj: dict[str, object]) -> LineageEdge:
    return LineageEdge(
        source=_ref_from_str(str(obj["source"])),
        target=_ref_from_str(str(obj["target"])),
        job_id=str(obj.get("job_id", "")),
        transform=str(obj.get("transform", "")),
    )


# ── JSONL I/O ─────────────────────────────────────────────────────────────────


def write_sources(sources: list[DataSource], fh: IO[str]) -> None:
    for s in sources:
        fh.write(json.dumps(source_to_dict(s)) + "\n")


def read_sources(fh: IO[str]) -> list[DataSource]:
    out: list[DataSource] = []
    for line in fh:
        line = line.strip()
        if line:
            out.append(source_from_dict(json.loads(line)))
    return out


def write_edges(edges: list[LineageEdge], fh: IO[str]) -> None:
    for e in edges:
        fh.write(json.dumps(edge_to_dict(e)) + "\n")


def read_edges(fh: IO[str]) -> list[LineageEdge]:
    out: list[LineageEdge] = []
    for line in fh:
        line = line.strip()
        if line:
            out.append(edge_from_dict(json.loads(line)))
    return out
