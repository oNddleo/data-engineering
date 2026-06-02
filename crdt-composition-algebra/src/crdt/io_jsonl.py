"""JSONL serialisation for CRDT snapshots."""

from __future__ import annotations

import json
from typing import IO

from crdt.crdts import GCounter, GSet, PNCounter


def gcounter_to_dict(c: GCounter) -> dict[str, object]:
    return c.to_dict()


def gcounter_from_dict(obj: dict[str, object]) -> GCounter:
    counts = obj.get("counts", {})
    if not isinstance(counts, dict):
        raise TypeError("counts must be a dict")
    return GCounter({str(k): int(v) for k, v in counts.items()})


def pncounter_to_dict(c: PNCounter) -> dict[str, object]:
    return c.to_dict()


def pncounter_from_dict(obj: dict[str, object]) -> PNCounter:
    inc_raw = obj.get("inc", {})
    dec_raw = obj.get("dec", {})
    if not isinstance(inc_raw, dict) or not isinstance(dec_raw, dict):
        raise TypeError("inc/dec must be dicts")
    return PNCounter(gcounter_from_dict(inc_raw), gcounter_from_dict(dec_raw))


def gset_from_dict(obj: dict[str, object]) -> GSet:
    elems = obj.get("elements", [])
    if not isinstance(elems, list):
        raise TypeError("elements must be a list")
    return GSet(frozenset(str(e) for e in elems))


def write_snapshot(snapshots: list[dict[str, object]], fh: IO[str]) -> None:
    for snap in snapshots:
        fh.write(json.dumps(snap) + "\n")


def read_snapshot(fh: IO[str]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for line in fh:
        line = line.strip()
        if line:
            obj = json.loads(line)
            if isinstance(obj, dict):
                out.append(obj)
    return out
