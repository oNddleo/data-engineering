"""``vncustoms`` CLI: info | tariff | calc | simulate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from vncustoms.calc import compute
from vncustoms.io_jsonl import dump_calcs, dump_declarations, load_declarations
from vncustoms.simulator import generate
from vncustoms.tariff import duty_rate_for, vat_rate_for


def _cmd_info(_: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "name": "vn-customs-declaration-pipeline",
                "version": "0.1.0",
                "subcommands": ["info", "tariff", "calc", "simulate"],
            },
            indent=2,
        ),
    )
    return 0


def _cmd_tariff(ns: argparse.Namespace) -> int:
    chapter = ns.chapter
    print(
        json.dumps(
            {
                "chapter": chapter,
                "duty_rate": duty_rate_for(chapter),
                "vat_rate": vat_rate_for(chapter),
            }
        ),
    )
    return 0


def _cmd_simulate(ns: argparse.Namespace) -> int:
    decls = generate(n=ns.n, seed=ns.seed)
    Path(ns.output).write_text(dump_declarations(decls), encoding="utf-8")
    print(json.dumps({"count": len(decls), "output": ns.output}))
    return 0


def _cmd_calc(ns: argparse.Namespace) -> int:
    decls = load_declarations(Path(ns.input).read_text(encoding="utf-8"))
    calcs = [compute(d) for d in decls]
    Path(ns.output).write_text(dump_calcs(calcs), encoding="utf-8")
    total_tax = sum(c.total_tax_vnd for c in calcs)
    print(json.dumps({"count": len(calcs), "total_tax_vnd": total_tax}))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vncustoms")
    sub = p.add_subparsers(dest="cmd", required=True)

    info = sub.add_parser("info")
    info.set_defaults(func=_cmd_info)

    tariff = sub.add_parser("tariff")
    tariff.add_argument("chapter", help="2-digit HS chapter, e.g. '85'")
    tariff.set_defaults(func=_cmd_tariff)

    sim = sub.add_parser("simulate")
    sim.add_argument("--n", type=int, default=50)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", required=True)
    sim.set_defaults(func=_cmd_simulate)

    calc = sub.add_parser("calc")
    calc.add_argument("--input", required=True)
    calc.add_argument("--output", required=True)
    calc.set_defaults(func=_cmd_calc)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    rc: int = ns.func(ns)
    return rc


if __name__ == "__main__":
    sys.exit(main())
