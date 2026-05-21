"""JSONL codec for SchemaEntry."""

from __future__ import annotations

import json

from schemreg.registry import SchemaEntry


def entry_to_dict(e: SchemaEntry) -> dict[str, object]:
    return {
        "subject": e.subject,
        "version": e.version,
        "schema": e.schema,
        "created_at_ms": e.created_at_ms,
    }


def entry_from_dict(d: object) -> SchemaEntry:
    if not isinstance(d, dict):
        raise TypeError(f"expected dict, got {type(d)}")
    subject = d.get("subject")
    if not isinstance(subject, str):
        raise TypeError("subject must be str")
    version = d.get("version")
    if not isinstance(version, int):
        raise TypeError("version must be int")
    schema_raw = d.get("schema")
    if not isinstance(schema_raw, dict):
        raise TypeError("schema must be dict")
    schema = {str(k): str(v) for k, v in schema_raw.items()}
    created = d.get("created_at_ms", 0)
    if not isinstance(created, int):
        raise TypeError("created_at_ms must be int")
    return SchemaEntry(
        subject=subject,
        version=version,
        schema=schema,
        created_at_ms=created,
    )


def dump(entries: list[SchemaEntry]) -> str:
    lines = [json.dumps(entry_to_dict(e), ensure_ascii=False) for e in entries]
    return "\n".join(lines) + ("\n" if lines else "")


def load(text: str) -> list[SchemaEntry]:
    out: list[SchemaEntry] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise TypeError(f"Expected JSON object, got {type(raw)}")
        out.append(entry_from_dict(raw))
    return out
