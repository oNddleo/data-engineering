"""Type-inference engine.

The algorithm: for each column, walk the rows once and keep a vote
counter per candidate type. A type wins the column if **every
non-empty cell** parses as that type. We try types in order of
specificity:

```
BOOL → INT → DATE → DATETIME → DECIMAL → FLOAT → STRING (fallback)
```

(specifically: a single non-bool cell disqualifies BOOL; a single
non-int cell disqualifies INT; etc).

We also track:

* **Nullability** — ``True`` if any cell was empty after strip.
* **Distinct cardinality** — counted exactly up to ``MAX_CARDINALITY``,
  beyond which we return ``MAX_CARDINALITY + 1``.
* **Examples** — first five distinct non-null values (insertion order).
* **min / max** — for INT/FLOAT/DECIMAL/DATE/DATETIME, computed in
  the natural ordering of the parsed type.
* **detected_format** — the format string of the first recognised
  DATE / DATETIME cell.

The full pipeline lives in ``infer_schema()`` which orchestrates
read → infer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from csvinf.parsers import (
    detect_date_format,
    detect_datetime_format,
    try_bool,
    try_date,
    try_datetime,
    try_decimal,
    try_float,
    try_int,
)
from csvinf.reader import read
from csvinf.schema import (
    MAX_CARDINALITY,
    ColumnType,
    InferredColumn,
    InferredSchema,
)

if TYPE_CHECKING:
    from datetime import date, datetime


def infer_schema(
    text: str,
    *,
    source_name: str = "stream",
    max_rows: int | None = None,
) -> InferredSchema:
    """Read ``text`` and infer per-column types.

    ``max_rows=None`` uses all rows.
    """
    rr = read(text, max_rows=max_rows)
    if not rr.column_names:
        return InferredSchema(
            source_name=source_name,
            delimiter=rr.delimiter,
            has_header=rr.has_header,
            n_rows_scanned=0,
            columns=(),
        )
    columns: list[InferredColumn] = []
    for col_idx, name in enumerate(rr.column_names):
        column_cells = [(row[col_idx] if col_idx < len(row) else "").strip() for row in rr.rows]
        columns.append(_infer_column(name, column_cells))
    return InferredSchema(
        source_name=source_name,
        delimiter=rr.delimiter,
        has_header=rr.has_header,
        n_rows_scanned=len(rr.rows),
        columns=tuple(columns),
    )


def _infer_column(name: str, cells: list[str]) -> InferredColumn:
    """Pure column-wise inference over a list of raw cells."""
    n_rows = len(cells)
    non_null_cells = [c for c in cells if c]
    n_non_null = len(non_null_cells)
    nullable = n_non_null < n_rows

    # Distinct counting (capped).
    distinct: dict[str, None] = {}
    for c in non_null_cells:
        if c not in distinct:
            distinct[c] = None
            if len(distinct) > MAX_CARDINALITY:
                break
    cardinality = len(distinct) if len(distinct) <= MAX_CARDINALITY else MAX_CARDINALITY + 1
    examples = tuple(list(distinct.keys())[:5])

    detected, min_v, max_v, fmt = _detect_type_min_max(non_null_cells)
    return InferredColumn(
        name=name,
        type=detected,
        nullable=nullable,
        n_rows=n_rows,
        n_non_null=n_non_null,
        cardinality=cardinality,
        examples=examples,
        min_value=min_v,
        max_value=max_v,
        detected_format=fmt,
    )


def _detect_type_min_max(
    cells: list[str],
) -> tuple[ColumnType, str, str, str]:
    """Return ``(type, min_string, max_string, detected_format)``.

    All non-null cells must parse as the chosen type; if any fails we
    fall through to the next.
    """
    if not cells:
        return ColumnType.STRING, "", "", ""

    # BOOL — true only if every cell is a boolean
    if all(try_bool(c) is not None for c in cells):
        return ColumnType.BOOL, "", "", ""

    # INT — every cell parses as integer
    int_values = [try_int(c) for c in cells]
    if all(v is not None for v in int_values):
        ints = [v for v in int_values if v is not None]
        return ColumnType.INT, str(min(ints)), str(max(ints)), ""

    # DATE — every cell parses as date
    date_values = [try_date(c) for c in cells]
    if all(v is not None for v in date_values):
        dates = [v for v in date_values if v is not None]
        fmt = detect_date_format(cells[0])
        return ColumnType.DATE, str(min(dates)), str(max(dates)), fmt

    # DATETIME — every cell parses as datetime
    dt_values = [try_datetime(c) for c in cells]
    if all(v is not None for v in dt_values):
        dts = [v for v in dt_values if v is not None]
        fmt = detect_datetime_format(cells[0])
        return ColumnType.DATETIME, _safe_iso(min(dts)), _safe_iso(max(dts)), fmt

    # DECIMAL — every cell parses as VN decimal
    dec_values = [try_decimal(c) for c in cells]
    if all(v is not None for v in dec_values):
        # min/max in numeric order; safe to use float for compare since
        # we're only ranking strings here, not arithmetic.
        decs = [v for v in dec_values if v is not None]
        decs.sort(key=float)
        return ColumnType.DECIMAL, decs[0], decs[-1], ""

    # FLOAT — every cell parses as float (EN locale)
    float_values = [try_float(c) for c in cells]
    if all(v is not None for v in float_values):
        floats = [v for v in float_values if v is not None]
        return ColumnType.FLOAT, str(min(floats)), str(max(floats)), ""

    return ColumnType.STRING, "", "", ""


def _safe_iso(v: date | datetime) -> str:
    return v.isoformat()


__all__ = ["infer_schema"]
