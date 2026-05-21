"""``vngrade`` CLI: info | classify | summarize | simulate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from vngrade.classify import classify, gpa
from vngrade.io_jsonl import dump, load
from vngrade.simulator import generate


def _cmd_info(_: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "name": "vn-school-grade-pipeline",
                "version": "0.1.0",
                "subcommands": ["info", "classify", "summarize", "simulate"],
            },
            indent=2,
        )
    )
    return 0


def _cmd_classify(ns: argparse.Namespace) -> int:
    reports = load(Path(ns.input).read_text(encoding="utf-8"))
    rows = [
        {
            "student_id": r.student_id,
            "classification": classify(r).value,
            "gpa": round(gpa(r), 2),
        }
        for r in reports
    ]
    Path(ns.output).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    counts: dict[str, int] = {}
    for row in rows:
        c = row["classification"]
        assert isinstance(c, str)
        counts[c] = counts.get(c, 0) + 1
    print(json.dumps({"count": len(rows), "by_classification": counts}))
    return 0


def _cmd_summarize(ns: argparse.Namespace) -> int:
    reports = load(Path(ns.input).read_text(encoding="utf-8"))
    classifications: dict[str, int] = {}
    conducts: dict[str, int] = {}
    total_gpa = 0.0
    for r in reports:
        c = classify(r).value
        classifications[c] = classifications.get(c, 0) + 1
        conducts[r.conduct.value] = conducts.get(r.conduct.value, 0) + 1
        total_gpa += gpa(r)
    avg_gpa = total_gpa / len(reports) if reports else 0.0
    print(
        json.dumps(
            {
                "n_reports": len(reports),
                "avg_gpa": round(avg_gpa, 2),
                "by_classification": classifications,
                "by_conduct": conducts,
            }
        )
    )
    return 0


def _cmd_simulate(ns: argparse.Namespace) -> int:
    reports = generate(n=ns.n, seed=ns.seed)
    Path(ns.output).write_text(dump(reports), encoding="utf-8")
    print(json.dumps({"count": len(reports), "output": ns.output}))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vngrade")
    sub = p.add_subparsers(dest="cmd", required=True)

    info = sub.add_parser("info")
    info.set_defaults(func=_cmd_info)

    cls = sub.add_parser("classify")
    cls.add_argument("--input", required=True)
    cls.add_argument("--output", required=True)
    cls.set_defaults(func=_cmd_classify)

    sm = sub.add_parser("summarize")
    sm.add_argument("--input", required=True)
    sm.set_defaults(func=_cmd_summarize)

    sim = sub.add_parser("simulate")
    sim.add_argument("--n", type=int, default=100)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", required=True)
    sim.set_defaults(func=_cmd_simulate)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    rc: int = ns.func(ns)
    return rc


if __name__ == "__main__":
    sys.exit(main())
