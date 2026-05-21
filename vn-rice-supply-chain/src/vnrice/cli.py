"""CLI: vnrice."""

from __future__ import annotations

import argparse
import json
import sys


def _cmd_varieties(_args: argparse.Namespace) -> None:
    from vnrice.schema import MilledRiceSpec, PaddyGrade, RiceVariety

    print(
        json.dumps(
            {
                "varieties": [v.value for v in RiceVariety],
                "grades": [g.value for g in PaddyGrade],
                "broken_specs": [s.value for s in MilledRiceSpec],
            }
        )
    )


def _cmd_price(args: argparse.Namespace) -> None:
    from vnrice.milling import mill
    from vnrice.pricing import quote_export
    from vnrice.schema import MilledRiceSpec, PaddyGrade, PaddyLot, RiceVariety

    lot = PaddyLot(
        lot_id=args.lot_id,
        variety=RiceVariety(args.variety),
        grade=PaddyGrade(args.grade),
        weight_mt=args.weight_mt,
        moisture_pct=args.moisture_pct,
        price_vnd_per_kg=args.price_vnd,
    )
    milled = mill(lot, MilledRiceSpec(args.broken_spec))
    q = quote_export(milled, freight_usd_mt=args.freight)
    print(
        json.dumps(
            {
                "lot_id": lot.lot_id,
                "dry_weight_mt": milled.dry_weight_mt,
                "white_rice_mt": milled.white_rice_mt,
                "milling_yield_pct": milled.milling_yield_pct,
                "fob_price_usd_mt": q.fob_price_usd_mt,
                "total_fob_usd": q.total_fob_usd,
                "gross_margin_usd": q.gross_margin_usd,
            }
        )
    )


def _cmd_simulate(args: argparse.Namespace) -> None:
    from vnrice.simulator import generate, summarise

    quotes = generate(n=args.n, seed=args.seed)
    stats = summarise(quotes)
    print(
        json.dumps(
            {
                "n_lots": stats.n_lots,
                "total_paddy_mt": stats.total_paddy_mt,
                "total_white_rice_mt": stats.total_white_rice_mt,
                "avg_milling_yield_pct": stats.avg_milling_yield_pct,
                "total_fob_usd": stats.total_fob_usd,
                "total_gross_margin_usd": stats.total_gross_margin_usd,
            }
        )
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="vnrice")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("varieties")

    pp = sub.add_parser("price")
    pp.add_argument("--lot-id", default="LOT-001", dest="lot_id")
    pp.add_argument("--variety", default="JASMINE")
    pp.add_argument("--grade", default="GRADE_1")
    pp.add_argument("--weight-mt", type=float, default=100.0, dest="weight_mt")
    pp.add_argument("--moisture-pct", type=float, default=14.0, dest="moisture_pct")
    pp.add_argument("--price-vnd", type=float, default=7500.0, dest="price_vnd")
    pp.add_argument("--broken-spec", default="5%", dest="broken_spec")
    pp.add_argument("--freight", type=float, default=0.0)

    sp = sub.add_parser("simulate")
    sp.add_argument("--n", type=int, default=50)
    sp.add_argument("--seed", type=int, default=0)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "varieties":
            _cmd_varieties(args)
        elif args.cmd == "price":
            _cmd_price(args)
        elif args.cmd == "simulate":
            _cmd_simulate(args)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
