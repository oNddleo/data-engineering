"""JSONL codec for KLL sketch serialisation."""

from __future__ import annotations

import json

from kllsketch.sketch import KLLSketch


def sketch_to_dict(s: KLLSketch) -> dict[str, object]:
    return {
        "k": s.k,
        "n": s.n,
        "compactors": [list(c) for c in s._compactors],
    }


def sketch_from_dict(d: object) -> KLLSketch:
    if not isinstance(d, dict):
        raise TypeError(f"expected dict, got {type(d)}")
    k = d.get("k")
    if not isinstance(k, int):
        raise TypeError("k must be int")
    n = d.get("n")
    if not isinstance(n, int):
        raise TypeError("n must be int")
    compactors_raw = d.get("compactors")
    if not isinstance(compactors_raw, list):
        raise TypeError("compactors must be list")
    s = KLLSketch(k=k)
    s._compactors = []
    for lvl in compactors_raw:
        if not isinstance(lvl, list):
            raise TypeError("each compactor must be a list")
        s._compactors.append([float(v) for v in lvl])
    s._n = n
    return s


def dump(sketches: list[KLLSketch]) -> str:
    lines = [json.dumps(sketch_to_dict(s), ensure_ascii=False) for s in sketches]
    return "\n".join(lines) + ("\n" if lines else "")


def load(text: str) -> list[KLLSketch]:
    out: list[KLLSketch] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise TypeError(f"Expected JSON object, got {type(raw)}")
        out.append(sketch_from_dict(raw))
    return out
