"""CLI entry point: vnship."""

from __future__ import annotations

import argparse
import json
import sys


def _cmd_carriers(_args: argparse.Namespace) -> None:
    from vnship.schema import Carrier, ServiceType, ZoneType

    info = {
        "carriers": [c.value for c in Carrier],
        "services": [s.value for s in ServiceType],
        "zones": [z.value for z in ZoneType],
    }
    print(json.dumps(info, ensure_ascii=False))


def _cmd_price(args: argparse.Namespace) -> None:
    from vnship.pricing import calculate_fee
    from vnship.schema import Carrier, ServiceType, ShipmentRequest, ZoneType

    req = ShipmentRequest(
        carrier=Carrier(args.carrier),
        service=ServiceType(args.service),
        zone=ZoneType(args.zone),
        weight_g=args.weight_g,
        declared_value_vnd=args.declared_value,
        cod_amount_vnd=args.cod_amount,
        is_fragile=args.fragile,
    )
    result = calculate_fee(req)
    print(
        json.dumps(
            {
                "base_fee_vnd": result.base_fee_vnd,
                "weight_surcharge_vnd": result.weight_surcharge_vnd,
                "cod_fee_vnd": result.cod_fee_vnd,
                "fragile_surcharge_vnd": result.fragile_surcharge_vnd,
                "total_fee_vnd": result.total_fee_vnd,
            },
            ensure_ascii=False,
        )
    )


def _cmd_simulate(args: argparse.Namespace) -> None:
    from vnship.simulator import generate, summarise

    results = generate(n=args.n, seed=args.seed)
    stats = summarise(results)
    print(
        json.dumps(
            {
                "n_shipments": stats.n_shipments,
                "total_fee_vnd": stats.total_fee_vnd,
                "avg_fee_vnd": round(stats.avg_fee_vnd, 2),
                "carrier_counts": stats.carrier_counts,
                "cod_count": stats.cod_count,
            },
            ensure_ascii=False,
        )
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="vnship", description="VN Shipping Pipeline CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("carriers", help="List available carriers and services")

    pp = sub.add_parser("price", help="Price a single shipment")
    pp.add_argument("--carrier", required=True, help="Carrier code")
    pp.add_argument("--service", default="STANDARD", help="Service type")
    pp.add_argument("--zone", default="INNER_CITY", help="Zone type")
    pp.add_argument("--weight-g", type=int, required=True, dest="weight_g")
    pp.add_argument("--declared-value", type=int, default=0, dest="declared_value")
    pp.add_argument("--cod-amount", type=int, default=0, dest="cod_amount")
    pp.add_argument("--fragile", action="store_true", default=False)

    sp = sub.add_parser("simulate", help="Run a synthetic shipment batch")
    sp.add_argument("--n", type=int, default=100)
    sp.add_argument("--seed", type=int, default=0)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "carriers":
            _cmd_carriers(args)
        elif args.cmd == "price":
            _cmd_price(args)
        elif args.cmd == "simulate":
            _cmd_simulate(args)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
