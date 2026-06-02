"""CLI: vncoffee."""

from __future__ import annotations

import argparse
import json
import sys


def _cmd_grades(_args: argparse.Namespace) -> None:
    from vncoffee.schema import CoffeeGrade, CoffeeSpecies, ContractType, Incoterm

    print(
        json.dumps(
            {
                "species": [s.value for s in CoffeeSpecies],
                "grades": [g.value for g in CoffeeGrade],
                "contracts": [c.value for c in ContractType],
                "incoterms": [i.value for i in Incoterm],
            }
        )
    )


def _cmd_price(args: argparse.Namespace) -> None:
    from vncoffee.pricing import price_lot
    from vncoffee.schema import (
        CoffeeGrade,
        CoffeeSpecies,
        ContractType,
        ExportLot,
        Incoterm,
    )

    lot = ExportLot(
        lot_id=args.lot_id,
        species=CoffeeSpecies(args.species),
        grade=CoffeeGrade(args.grade),
        contract=ContractType(args.contract),
        incoterm=Incoterm(args.incoterm),
        volume_mt=args.volume_mt,
        futures_price_usd_mt=args.futures_price,
        differential_usd_mt=args.differential,
        fixed_price_usd_mt=args.fixed_price,
        freight_usd_mt=args.freight,
        insurance_rate_pct=args.insurance_rate,
    )
    p = price_lot(lot)
    print(
        json.dumps(
            {
                "lot_id": lot.lot_id,
                "fob_price_usd_mt": p.fob_price_usd_mt,
                "total_fob_usd": p.total_fob_usd,
                "total_contract_usd": p.total_contract_usd,
            }
        )
    )


def _cmd_simulate(args: argparse.Namespace) -> None:
    from vncoffee.simulator import generate, summarise

    lots = generate(n=args.n, seed=args.seed)
    stats = summarise(lots)
    print(
        json.dumps(
            {
                "n_lots": stats.n_lots,
                "total_volume_mt": stats.total_volume_mt,
                "total_value_usd": stats.total_value_usd,
                "avg_fob_usd_mt": stats.avg_fob_usd_mt,
                "species_counts": stats.species_counts,
            }
        )
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="vncoffee")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("grades", help="List grades, species, contracts")

    pp = sub.add_parser("price", help="Price a single export lot")
    pp.add_argument("--lot-id", default="LOT-001", dest="lot_id")
    pp.add_argument("--species", default="ROBUSTA")
    pp.add_argument("--grade", default="R1")
    pp.add_argument("--contract", default="DIFFERENTIAL")
    pp.add_argument("--incoterm", default="FOB")
    pp.add_argument("--volume-mt", type=float, default=100.0, dest="volume_mt")
    pp.add_argument("--futures-price", type=float, default=2800.0, dest="futures_price")
    pp.add_argument("--differential", type=float, default=0.0)
    pp.add_argument("--fixed-price", type=float, default=0.0, dest="fixed_price")
    pp.add_argument("--freight", type=float, default=0.0)
    pp.add_argument("--insurance-rate", type=float, default=0.0, dest="insurance_rate")

    sp = sub.add_parser("simulate", help="Simulate a batch of export lots")
    sp.add_argument("--n", type=int, default=50)
    sp.add_argument("--seed", type=int, default=0)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "grades":
            _cmd_grades(args)
        elif args.cmd == "price":
            _cmd_price(args)
        elif args.cmd == "simulate":
            _cmd_simulate(args)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
