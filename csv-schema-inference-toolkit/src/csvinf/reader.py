"""CSV reader with delimiter / header / encoding detection.

A very small wrapper over stdlib ``csv`` that:

1. **Sniffs the delimiter** — tries ``,``, ``;``, ``\\t``, ``|`` and
   picks the one with the most consistent column count across the
   first 20 lines. Returns ``,`` on a tie.
2. **Sniffs the header** — declares a header if every cell on the
   first row is a non-empty string AND row 2 has at least one cell
   that doesn't parse as the same type as row 1 (i.e. row 1 looks
   like names, row 2 looks like data).
3. **Reads** the whole file (or first N rows) into a list of dicts
   keyed by header name (or by positional ``"col_0"``, ``"col_1"``,
   … when no header).

For VN encoding compatibility the reader accepts pre-decoded ``str``
input. Callers responsible for opening the file with the right
encoding (UTF-8 with BOM, Windows-1258 for older systems).
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

from csvinf.parsers import (
    try_bool,
    try_date,
    try_datetime,
    try_decimal,
    try_float,
    try_int,
)

_CANDIDATE_DELIMITERS: tuple[str, ...] = (",", ";", "\t", "|")
_SNIFF_LINES = 20

# An "identifier-like" header name: starts with a letter or underscore;
# subsequent characters are letters, digits, underscores, hyphens, or spaces.
# Unicode-aware so VN column names like "Tên" / "địa_chỉ" pass.
_IDENTIFIER_RE = re.compile(r"^[^\W\d_][\w\- ]*$", re.UNICODE)


@dataclass(frozen=True, slots=True)
class ReadResult:
    """The result of reading a CSV stream."""

    delimiter: str
    has_header: bool
    column_names: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]  # raw cell values, untyped


def sniff_delimiter(text: str) -> str:
    """Return the delimiter producing the most consistent column count.

    Considers the first ``_SNIFF_LINES`` non-empty lines.
    """
    lines = [line for line in text.splitlines()[:_SNIFF_LINES] if line.strip()]
    if not lines:
        return ","
    best_delim = ","
    best_score = -1.0
    for delim in _CANDIDATE_DELIMITERS:
        counts = [len(_parse_row(line, delim)) for line in lines]
        if max(counts) < 2:
            continue  # delimiter not present
        # Consistency = -variance; prefer wider rows on a tie.
        mean = sum(counts) / len(counts)
        variance = sum((c - mean) ** 2 for c in counts) / len(counts)
        score = mean - variance * 10
        if score > best_score:
            best_score = score
            best_delim = delim
    return best_delim


def sniff_has_header(text: str, delimiter: str) -> bool:
    """Heuristic for whether the first row looks like a header.

    Returns ``True`` when either of the following holds:

    1. Row 1 has all non-empty, non-typed cells AND row 2 has at
       least one typed (numeric / date / bool / datetime) cell.
    2. Row 1 has all non-empty, non-typed cells AND every row 1
       cell looks like an **identifier name** (letter/underscore
       prefix, letters/digits/underscore/hyphen/space afterward).

    Case 1 catches typical mixed-type CSVs; case 2 catches the
    all-string case where row 1 names look obviously like column
    labels.
    """
    lines = [line for line in text.splitlines()[:_SNIFF_LINES] if line.strip()]
    if len(lines) < 2:
        return False
    first = _parse_row(lines[0], delimiter)
    second = _parse_row(lines[1], delimiter)
    if not first or any(not c.strip() for c in first):
        return False
    if any(_looks_typed(c) for c in first):
        return False
    if any(_looks_typed(c) for c in second):
        return True
    # Fallback: both rows all-string. Treat as header iff row 1
    # entries all look like identifier names.
    return all(_IDENTIFIER_RE.match(c.strip()) for c in first)


def read(text: str, *, max_rows: int | None = None) -> ReadResult:
    """Read a CSV stream and return delimiter + header + rows.

    ``max_rows=None`` reads the entire stream.
    """
    delim = sniff_delimiter(text)
    has_header = sniff_has_header(text, delim)
    reader = csv.reader(io.StringIO(text), delimiter=delim)
    all_rows: list[tuple[str, ...]] = [tuple(r) for r in reader]
    if not all_rows:
        return ReadResult(delimiter=delim, has_header=False, column_names=(), rows=())
    if has_header:
        header = all_rows[0]
        body = all_rows[1:]
        if max_rows is not None:
            body = body[:max_rows]
        return ReadResult(
            delimiter=delim,
            has_header=True,
            column_names=tuple(header),
            rows=tuple(body),
        )
    width = max(len(r) for r in all_rows)
    header_synth = tuple(f"col_{i}" for i in range(width))
    body = all_rows
    if max_rows is not None:
        body = body[:max_rows]
    return ReadResult(
        delimiter=delim,
        has_header=False,
        column_names=header_synth,
        rows=tuple(body),
    )


def _parse_row(line: str, delimiter: str) -> list[str]:
    """Split one line using the stdlib CSV state machine."""
    reader = csv.reader(io.StringIO(line), delimiter=delimiter)
    try:
        return next(reader)
    except StopIteration:
        return []


def _looks_typed(cell: str) -> bool:
    """``True`` if ``cell`` parses as anything but a string."""
    if not cell:
        return False
    if try_bool(cell) is not None:
        return True
    if try_int(cell) is not None:
        return True
    if try_float(cell) is not None:
        return True
    if try_decimal(cell) is not None:
        return True
    if try_date(cell) is not None:
        return True
    return try_datetime(cell) is not None


__all__ = ["ReadResult", "read", "sniff_delimiter", "sniff_has_header"]
