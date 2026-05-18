"""JSONL codec for InferredSchema / InferredColumn."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from csvinf.schema import ColumnType, InferredColumn, InferredSchema

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def _require_bool(d: dict[str, object], key: str) -> bool:
    v = d[key]
    if not isinstance(v, bool):
        raise TypeError(f"{key} must be bool, got {type(v).__name__}")
    return v


def column_to_dict(c: InferredColumn) -> dict[str, object]:
    return {
        "name": c.name,
        "type": c.type.value,
        "nullable": c.nullable,
        "n_rows": c.n_rows,
        "n_non_null": c.n_non_null,
        "cardinality": c.cardinality,
        "examples": list(c.examples),
        "min_value": c.min_value,
        "max_value": c.max_value,
        "detected_format": c.detected_format,
    }


def column_from_dict(d: dict[str, object]) -> InferredColumn:
    examples = d.get("examples", [])
    if not isinstance(examples, list):
        raise TypeError("examples must be list")
    return InferredColumn(
        name=_require_str(d, "name"),
        type=ColumnType(_require_str(d, "type")),
        nullable=_require_bool(d, "nullable"),
        n_rows=_require_int(d, "n_rows"),
        n_non_null=_require_int(d, "n_non_null"),
        cardinality=_require_int(d, "cardinality"),
        examples=tuple(str(e) for e in examples),
        min_value=_require_str(d, "min_value") if "min_value" in d else "",
        max_value=_require_str(d, "max_value") if "max_value" in d else "",
        detected_format=_require_str(d, "detected_format") if "detected_format" in d else "",
    )


def schema_to_dict(s: InferredSchema) -> dict[str, object]:
    return {
        "source_name": s.source_name,
        "delimiter": s.delimiter,
        "has_header": s.has_header,
        "n_rows_scanned": s.n_rows_scanned,
        "columns": [column_to_dict(c) for c in s.columns],
    }


def schema_from_dict(d: dict[str, object]) -> InferredSchema:
    cols_raw = d.get("columns", [])
    if not isinstance(cols_raw, list):
        raise TypeError("columns must be list")
    cols_list: list[InferredColumn] = []
    for c in cols_raw:
        if not isinstance(c, dict):
            raise TypeError(f"column must be dict, got {type(c).__name__}")
        cols_list.append(column_from_dict(c))
    columns = tuple(cols_list)
    return InferredSchema(
        source_name=_require_str(d, "source_name"),
        delimiter=_require_str(d, "delimiter"),
        has_header=_require_bool(d, "has_header"),
        n_rows_scanned=_require_int(d, "n_rows_scanned"),
        columns=columns,
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_schemas(items: Iterable[InferredSchema]) -> str:
    return _dump(schema_to_dict(s) for s in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_schemas(text: str) -> list[InferredSchema]:
    return [schema_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "column_from_dict",
    "column_to_dict",
    "dump_schemas",
    "load_schemas",
    "schema_from_dict",
    "schema_to_dict",
]
