"""Watermark store: last-processed `updated_at` per table.

Persisted as a single JSON object in the warehouse bucket
(s3://<bucket>/_control/watermarks.json) so host runs and Airflow tasks share
the same state. Uses fsspec/s3fs (already pulled in by pyiceberg[s3fs]).
"""
from __future__ import annotations

import json

import fsspec

import settings

_EPOCH = "1970-01-01T00:00:00+00:00"


def _path() -> str:
    return f"s3://{settings.S3_BUCKET}/{settings.WATERMARK_KEY}"


def _fs() -> fsspec.AbstractFileSystem:
    return fsspec.filesystem("s3", **settings.s3fs_storage_options())


def load_all() -> dict[str, str]:
    fs = _fs()
    if not fs.exists(_path()):
        return {}
    with fs.open(_path(), "r") as fh:
        return json.load(fh)


def get(table: str) -> str:
    """Last watermark for a table, or epoch if never loaded."""
    return load_all().get(table, _EPOCH)


def set_many(updates: dict[str, str]) -> None:
    """Merge + persist watermark updates atomically (single object write)."""
    current = load_all()
    current.update(updates)
    fs = _fs()
    with fs.open(_path(), "w") as fh:
        json.dump(current, fh, indent=2)
