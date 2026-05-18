"""Type-checked JSONL codec for snapshots, changes, dimension rows."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from scdkit.schema import ChangeKind, DimensionChange, DimensionRow

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


def _optional_str(d: dict[str, object], key: str) -> str | None:
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str or null, got {type(v).__name__}")
    return v


def _optional_int(d: dict[str, object], key: str) -> int | None:
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int or null, got {type(v).__name__}")
    return v


def _require_bool(d: dict[str, object], key: str) -> bool:
    v = d.get(key, True)
    if not isinstance(v, bool):
        raise TypeError(f"{key} must be bool, got {type(v).__name__}")
    return v


def _require_str_dict(d: dict[str, object], key: str) -> dict[str, str]:
    """Read a flat ``str → str`` dict."""
    v = d.get(key, {})
    if not isinstance(v, dict):
        raise TypeError(f"{key} must be object, got {type(v).__name__}")
    out: dict[str, str] = {}
    for k, val in v.items():
        if not isinstance(k, str) or not isinstance(val, str):
            raise TypeError(f"{key} must be str→str")
        out[k] = val
    return out


def _optional_str_dict(d: dict[str, object], key: str) -> dict[str, str] | None:
    if key not in d or d[key] is None:
        return None
    return _require_str_dict(d, key)


def row_to_dict(r: DimensionRow) -> dict[str, object]:
    return {
        "natural_key": r.natural_key,
        "attributes": dict(r.attributes),
        "surrogate_key": r.surrogate_key,
        "effective_from": r.effective_from.isoformat() if r.effective_from else None,
        "effective_to": r.effective_to.isoformat() if r.effective_to else None,
        "is_current": r.is_current,
        "previous_attributes": dict(r.previous_attributes),
    }


def row_from_dict(d: dict[str, object]) -> DimensionRow:
    from_ts = _optional_str(d, "effective_from")
    to_ts = _optional_str(d, "effective_to")
    return DimensionRow(
        natural_key=_require_str(d, "natural_key"),
        attributes=_require_str_dict(d, "attributes"),
        surrogate_key=_optional_int(d, "surrogate_key"),
        effective_from=datetime.fromisoformat(from_ts) if from_ts else None,
        effective_to=datetime.fromisoformat(to_ts) if to_ts else None,
        is_current=_require_bool(d, "is_current"),
        previous_attributes=_require_str_dict(d, "previous_attributes"),
    )


def change_to_dict(c: DimensionChange) -> dict[str, object]:
    return {
        "natural_key": c.natural_key,
        "kind": c.kind.value,
        "detected_at": c.detected_at.isoformat(),
        "before": c.before,
        "after": c.after,
        "changed_attrs": list(c.changed_attrs),
    }


def change_from_dict(d: dict[str, object]) -> DimensionChange:
    raw_attrs = d.get("changed_attrs", [])
    if not isinstance(raw_attrs, list):
        raise TypeError("changed_attrs must be a list")
    return DimensionChange(
        natural_key=_require_str(d, "natural_key"),
        kind=ChangeKind(_require_str(d, "kind")),
        detected_at=datetime.fromisoformat(_require_str(d, "detected_at")),
        before=_optional_str_dict(d, "before"),
        after=_optional_str_dict(d, "after"),
        changed_attrs=tuple(a for a in raw_attrs if isinstance(a, str)),
    )


# Snapshot codec — one entity per JSONL line as ``{natural_key, attributes}``.
def snapshot_to_lines(snapshot: dict[str, dict[str, str]]) -> str:
    """Emit one JSONL entity per row."""
    lines = [
        json.dumps({"natural_key": nk, "attributes": dict(attrs)}, ensure_ascii=False)
        for nk, attrs in sorted(snapshot.items())
    ]
    return "\n".join(lines) + "\n"


def snapshot_from_text(text: str) -> dict[str, dict[str, str]]:
    """Inverse of :func:`snapshot_to_lines`."""
    out: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object, got {type(parsed).__name__}")
        nk = _require_str(parsed, "natural_key")
        out[nk] = _require_str_dict(parsed, "attributes")
    return out


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_rows(rows: Iterable[DimensionRow]) -> str:
    return _dump(row_to_dict(r) for r in rows)


def dump_changes(changes: Iterable[DimensionChange]) -> str:
    return _dump(change_to_dict(c) for c in changes)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_rows(text: str) -> Iterator[DimensionRow]:
    for d in _iter_lines(text):
        yield row_from_dict(d)


def load_changes(text: str) -> Iterator[DimensionChange]:
    for d in _iter_lines(text):
        yield change_from_dict(d)


__all__ = [
    "change_from_dict",
    "change_to_dict",
    "dump_changes",
    "dump_rows",
    "load_changes",
    "load_rows",
    "row_from_dict",
    "row_to_dict",
    "snapshot_from_text",
    "snapshot_to_lines",
]
