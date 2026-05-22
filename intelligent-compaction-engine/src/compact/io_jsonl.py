"""JSONL serialisation for compaction plans and table metadata."""

from __future__ import annotations

import json
from datetime import datetime
from typing import IO

from compact.schema import (
    CompactionAction,
    CompactionPlan,
    CompactionTask,
    DataFile,
    Partition,
    TableMeta,
)

# ── helpers ──────────────────────────────────────────────────────────────────


def _req_str(obj: dict[str, object], key: str) -> str:
    v = obj[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str")
    return v


def _req_int(obj: dict[str, object], key: str) -> int:
    v = obj[key]
    if not isinstance(v, int):
        raise TypeError(f"{key} must be int")
    return v


def _opt_int(obj: dict[str, object], key: str, default: int = 0) -> int:
    v = obj.get(key, default)
    if isinstance(v, int):
        return v
    return default


def _req_dt(obj: dict[str, object], key: str) -> datetime:
    v = obj[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be an ISO datetime string")
    return datetime.fromisoformat(v)


def _dt_str(dt: datetime) -> str:
    return dt.isoformat()


# ── DataFile ──────────────────────────────────────────────────────────────────


def datafile_to_dict(f: DataFile) -> dict[str, object]:
    return {
        "path": f.path,
        "size_bytes": f.size_bytes,
        "row_count": f.row_count,
        "partition": f.partition,
        "created_at": _dt_str(f.created_at),
        "last_modified": _dt_str(f.last_modified),
    }


def datafile_from_dict(obj: dict[str, object]) -> DataFile:
    return DataFile(
        path=_req_str(obj, "path"),
        size_bytes=_req_int(obj, "size_bytes"),
        row_count=_req_int(obj, "row_count"),
        partition=_req_str(obj, "partition"),
        created_at=_req_dt(obj, "created_at"),
        last_modified=_req_dt(obj, "last_modified"),
    )


# ── TableMeta ─────────────────────────────────────────────────────────────────


def tablemeta_to_dict(table: TableMeta) -> dict[str, object]:
    return {
        "table_name": table.table_name,
        "format": table.format,
        "columns": table.columns,
        "partitions": [
            {
                "key": p.key,
                "files": [datafile_to_dict(f) for f in p.files],
            }
            for p in table.partitions
        ],
    }


def tablemeta_from_dict(obj: dict[str, object]) -> TableMeta:
    raw_parts = obj.get("partitions", [])
    if not isinstance(raw_parts, list):
        raw_parts = []
    partitions: list[Partition] = []
    for rp in raw_parts:
        if not isinstance(rp, dict):
            continue
        raw_files = rp.get("files", [])
        files = [datafile_from_dict(f) for f in (raw_files if isinstance(raw_files, list) else [])]
        partitions.append(Partition(key=str(rp.get("key", "")), files=files))
    cols = obj.get("columns", [])
    if not isinstance(cols, list):
        cols = []
    return TableMeta(
        table_name=_req_str(obj, "table_name"),
        format=_req_str(obj, "format"),
        partitions=partitions,
        columns=[str(c) for c in cols],
    )


def load_tablemeta(fh: IO[str]) -> TableMeta:
    return tablemeta_from_dict(json.load(fh))


def dump_tablemeta(table: TableMeta, fh: IO[str]) -> None:
    json.dump(tablemeta_to_dict(table), fh, indent=2)


# ── CompactionPlan ───────────────────────────────────────────────────────────


def task_to_dict(t: CompactionTask) -> dict[str, object]:
    return {
        "action": t.action.value,
        "partition_key": t.partition_key,
        "target_files": t.target_files,
        "z_order_columns": t.z_order_columns,
        "priority": t.priority,
        "reason": t.reason,
    }


def plan_to_jsonl(plan: CompactionPlan, fh: IO[str]) -> None:
    meta = {
        "table_name": plan.table_name,
        "task_count": len(plan.tasks),
        "estimated_size_reduction_bytes": plan.estimated_size_reduction_bytes,
        "estimated_file_reduction": plan.estimated_file_reduction,
        "action_counts": plan.action_counts,
    }
    fh.write(json.dumps(meta) + "\n")
    for t in plan.tasks:
        fh.write(json.dumps(task_to_dict(t)) + "\n")


def plan_from_jsonl(fh: IO[str]) -> CompactionPlan:
    lines = [ln.strip() for ln in fh if ln.strip()]
    if not lines:
        raise ValueError("empty input")
    meta = json.loads(lines[0])
    tasks: list[CompactionTask] = []
    for line in lines[1:]:
        obj = json.loads(line)
        tasks.append(
            CompactionTask(
                action=CompactionAction(obj["action"]),
                partition_key=str(obj["partition_key"]),
                target_files=list(obj.get("target_files", [])),
                z_order_columns=list(obj.get("z_order_columns", [])),
                priority=float(obj.get("priority", 0.0)),
                reason=str(obj.get("reason", "")),
            )
        )
    return CompactionPlan(
        table_name=str(meta["table_name"]),
        tasks=tasks,
        estimated_size_reduction_bytes=int(meta.get("estimated_size_reduction_bytes", 0)),
        estimated_file_reduction=int(meta.get("estimated_file_reduction", 0)),
    )
