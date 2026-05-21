"""``vnfishery`` CLI: info | benchmark | dumping-watch | aggregate | simulate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from vnfishery.aggregate import aggregate_by_species_market
from vnfishery.benchmark import benchmark_usd_cents_per_kg, is_dumping_risk
from vnfishery.io_jsonl import dump_records, load_records
from vnfishery.schema import Grade, Market, Species
from vnfishery.simulator import generate


def _cmd_info(_: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "name": "vn-fishery-export-pipeline",
                "version": "0.1.0",
                "subcommands": [
                    "info",
                    "benchmark",
                    "dumping-watch",
                    "aggregate",
                    "simulate",
                ],
            },
            indent=2,
        )
    )
    return 0


def _cmd_benchmark(ns: argparse.Namespace) -> int:
    sp = Species(ns.species)
    mk = Market(ns.market)
    gr = Grade(ns.grade)
    price = benchmark_usd_cents_per_kg(sp, mk, gr)
    print(
        json.dumps(
            {
                "species": sp.value,
                "market": mk.value,
                "grade": gr.value,
                "benchmark_usd_cents_per_kg": price,
            }
        )
    )
    return 0


def _cmd_dumping_watch(ns: argparse.Namespace) -> int:
    records = load_records(Path(ns.input).read_text(encoding="utf-8"))
    flagged = [
        r
        for r in records
        if is_dumping_risk(r.species, r.market, r.grade, r.fob_price_usd_cents_per_kg)
    ]
    Path(ns.output).write_text(dump_records(flagged), encoding="utf-8")
    print(json.dumps({"total": len(records), "flagged": len(flagged)}))
    return 0


def _cmd_aggregate(ns: argparse.Namespace) -> int:
    records = load_records(Path(ns.input).read_text(encoding="utf-8"))
    agg = aggregate_by_species_market(records)
    rows = [
        {
            "species": sp.value,
            "market": mk.value,
            "n_shipments": v.n_shipments,
            "total_weight_kg": v.total_weight_kg,
            "total_fob_value_usd_cents": v.total_fob_value_usd_cents,
            "avg_price_usd_cents_per_kg": v.avg_price_usd_cents_per_kg,
        }
        for (sp, mk), v in agg.items()
    ]
    Path(ns.output).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"groups": len(rows)}))
    return 0


def _cmd_simulate(ns: argparse.Namespace) -> int:
    records = generate(n=ns.n, seed=ns.seed)
    Path(ns.output).write_text(dump_records(records), encoding="utf-8")
    print(json.dumps({"count": len(records), "output": ns.output}))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vnfishery")
    sub = p.add_subparsers(dest="cmd", required=True)

    info = sub.add_parser("info")
    info.set_defaults(func=_cmd_info)

    bench = sub.add_parser("benchmark")
    bench.add_argument("--species", required=True)
    bench.add_argument("--market", required=True)
    bench.add_argument("--grade", required=True)
    bench.set_defaults(func=_cmd_benchmark)

    dw = sub.add_parser("dumping-watch")
    dw.add_argument("--input", required=True)
    dw.add_argument("--output", required=True)
    dw.set_defaults(func=_cmd_dumping_watch)

    agg = sub.add_parser("aggregate")
    agg.add_argument("--input", required=True)
    agg.add_argument("--output", required=True)
    agg.set_defaults(func=_cmd_aggregate)

    sim = sub.add_parser("simulate")
    sim.add_argument("--n", type=int, default=50)
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
