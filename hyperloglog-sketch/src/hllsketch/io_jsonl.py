"""JSONL codec for HyperLogLog snapshots."""

from __future__ import annotations

import json

from hllsketch.sketch import HyperLogLog


def sketch_to_dict(h: HyperLogLog) -> dict[str, object]:
    return {
        "precision": h.precision,
        "registers": h._registers,
    }


def sketch_from_dict(d: object) -> HyperLogLog:
    if not isinstance(d, dict):
        raise TypeError(f"expected dict, got {type(d)}")

    prec = d.get("precision")
    if not isinstance(prec, int):
        raise TypeError("precision must be int")
    h = HyperLogLog(precision=prec)

    raw_regs = d.get("registers")
    if not isinstance(raw_regs, list):
        raise TypeError("registers must be list")
    if len(raw_regs) != h.num_registers:
        raise ValueError(f"expected {h.num_registers} registers, got {len(raw_regs)}")
    h._registers = [int(r) for r in raw_regs]
    return h


def dump(sketches: list[HyperLogLog]) -> str:
    lines = [json.dumps(sketch_to_dict(h), ensure_ascii=False) for h in sketches]
    return "\n".join(lines) + ("\n" if lines else "")


def load(text: str) -> list[HyperLogLog]:
    out: list[HyperLogLog] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise TypeError(f"Expected JSON object, got {type(raw)}")
        out.append(sketch_from_dict(raw))
    return out
