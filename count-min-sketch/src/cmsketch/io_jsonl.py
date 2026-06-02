"""JSONL codec for CountMinSketch snapshots."""

from __future__ import annotations

import json

from cmsketch.sketch import CountMinSketch


def sketch_to_dict(s: CountMinSketch) -> dict[str, object]:
    return {
        "width": s.width,
        "depth": s.depth,
        "seed": s.seed,
        "n": s.n,
        "table": s._table,
        "coeffs": [[a, b] for a, b in s._coeffs],
    }


def sketch_from_dict(d: object) -> CountMinSketch:
    if not isinstance(d, dict):
        raise TypeError(f"expected dict, got {type(d)}")

    def _i(k: str) -> int:
        v = d.get(k)
        if not isinstance(v, int):
            raise TypeError(f"{k} must be int")
        return v

    s = CountMinSketch(width=_i("width"), depth=_i("depth"), seed=_i("seed"))
    # Restore internal state
    raw_table = d.get("table")
    if not isinstance(raw_table, list):
        raise TypeError("table must be list")
    s._table = [[int(c) for c in row] for row in raw_table]
    s._n = _i("n")
    raw_coeffs = d.get("coeffs")
    if not isinstance(raw_coeffs, list):
        raise TypeError("coeffs must be list")
    s._coeffs = [(int(pair[0]), int(pair[1])) for pair in raw_coeffs]
    return s


def dump(sketches: list[CountMinSketch]) -> str:
    lines = [json.dumps(sketch_to_dict(s), ensure_ascii=False) for s in sketches]
    return "\n".join(lines) + ("\n" if lines else "")


def load(text: str) -> list[CountMinSketch]:
    out: list[CountMinSketch] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise TypeError(f"Expected JSON object, got {type(raw)}")
        out.append(sketch_from_dict(raw))
    return out
