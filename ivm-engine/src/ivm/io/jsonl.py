"""JSONL I/O for materialised view snapshots and update streams.

Snapshot format
---------------
Each line in a snapshot file is a JSON object with the fields of one
view record.  Snapshots capture the current state (positive-multiplicity
records only).

Update stream format
--------------------
Each line is a JSON object with:
  { "record": {...}, "timestamp": <int>, "diff": <int> }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ivm.types import Record, Update


def dump_snapshot(records: list[Record], path: str | Path) -> int:
    """Write view records to a JSONL file.

    Parameters
    ----------
    records : list[Record]
        The output of ``engine.query(view_name)``.
    path : str | Path
        Destination file path.  Will be overwritten if it exists.

    Returns
    -------
    int
        Number of records written.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, default=str) + "\n")
    return len(records)


def load_snapshot(path: str | Path) -> list[Record]:
    """Read a JSONL snapshot file back into a list of records.

    Parameters
    ----------
    path : str | Path
        Source file path.

    Returns
    -------
    list[Record]
    """
    p = Path(path)
    result: list[Record] = []
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                result.append(json.loads(line))
    return result


def read_jsonl_updates(path: str | Path) -> list[Update]:
    """Read a JSONL update-stream file into a list of Update objects.

    Each line must have the shape::

        { "record": {...}, "timestamp": <int>, "diff": <int> }

    Parameters
    ----------
    path : str | Path

    Returns
    -------
    list[Update]
    """
    from ivm.types import Update as _Update

    p = Path(path)
    result: list[Update] = []
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            result.append(_Update(obj["record"], int(obj["timestamp"]), int(obj["diff"])))
    return result
