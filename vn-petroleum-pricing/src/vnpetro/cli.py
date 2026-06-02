"""CLI: vnpetro."""

from __future__ import annotations

import argparse
import json
import sys


def _cmd_fuels(_args: argparse.Namespace) -> None:
    from vnpetro.schema import FuelType, PriceRegion

    print(
        json.dumps(
            {
                "fuel_types": [f.value for f in FuelType],
                "regions": [r.value for r in PriceRegion],
            }
        )
    )


def _cmd_price(args: argparse.Namespace) -> None:
    from vnpetro.pricing import calculate_retail_price
    from vnpetro.schema import FuelType, PriceInput, PriceRegion

    inp = PriceInput(
        fuel_type=FuelType(args.fuel_type),
        region=PriceRegion(args.region),
        cif_price_usd_per_barrel=args.cif,
        usd_to_vnd=args.usd_to_vnd,
        stabilisation_fund_vnd_per_litre=args.psf,
    )
    b = calculate_retail_price(inp)
    print(
        json.dumps(
            {
                "fuel_type": b.fuel_type.value,
                "region": b.region.value,
                "base_price_vnd": b.base_price_vnd,
                "sct_vnd": b.sct_vnd,
                "ept_vnd": b.ept_vnd,
                "vat_vnd": b.vat_vnd,
                "retail_price_vnd_per_litre": b.retail_price_vnd_per_litre,
                "retail_price_rounded": b.retail_price_rounded,
            }
        )
    )


def _cmd_simulate(args: argparse.Namespace) -> None:
    from vnpetro.simulator import generate, summarise

    breakdowns = generate(n=args.n, seed=args.seed)
    stats = summarise(breakdowns)
    print(
        json.dumps(
            {
                "n_scenarios": stats.n_scenarios,
                "avg_retail_vnd_per_litre": stats.avg_retail_vnd_per_litre,
                "max_retail_vnd_per_litre": stats.max_retail_vnd_per_litre,
                "min_retail_vnd_per_litre": stats.min_retail_vnd_per_litre,
            }
        )
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="vnpetro")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("fuels")

    pp = sub.add_parser("price")
    pp.add_argument("--fuel-type", default="RON95-III", dest="fuel_type")
    pp.add_argument("--region", default="SOUTH")
    pp.add_argument("--cif", type=float, default=85.0)
    pp.add_argument("--usd-to-vnd", type=float, default=24_500.0, dest="usd_to_vnd")
    pp.add_argument("--psf", type=float, default=0.0)

    sp = sub.add_parser("simulate")
    sp.add_argument("--n", type=int, default=50)
    sp.add_argument("--seed", type=int, default=0)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "fuels":
            _cmd_fuels(args)
        elif args.cmd == "price":
            _cmd_price(args)
        elif args.cmd == "simulate":
            _cmd_simulate(args)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
