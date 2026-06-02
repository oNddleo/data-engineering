"""``multiprice`` command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from multiprice.store import ObservationStore


def cmd_info(_args: argparse.Namespace) -> int:
    from multiprice import __version__

    print(f"multi-platform-price-tracker {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from multiprice.io_jsonl import dump_mappings, dump_observations
    from multiprice.simulator import generate

    mappings, obs = generate(
        n_skus=args.skus,
        n_snapshots=args.snapshots,
        snapshot_interval_hours=args.interval,
        seed=args.seed,
        arbitrage_skus=args.arbitrage,
        stockout_skus=args.stockouts,
    )
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "mappings.jsonl").write_text(dump_mappings(mappings), encoding="utf-8")
    (out_dir / "observations.jsonl").write_text(dump_observations(obs), encoding="utf-8")
    print(
        f"wrote {len(mappings)} mappings + {len(obs)} observations to {out_dir}/",
        file=sys.stderr,
    )
    return 0


def _load_store(directory: Path) -> ObservationStore:
    from multiprice.io_jsonl import load_observations
    from multiprice.store import ObservationStore

    store = ObservationStore()
    obs_path = directory / "observations.jsonl"
    if obs_path.exists():
        for o in load_observations(obs_path.read_text(encoding="utf-8")):
            store.append(o)
    return store


def cmd_changes(args: argparse.Namespace) -> int:
    from multiprice.detectors import detect_price_changes

    store = _load_store(Path(args.dataset))
    events = detect_price_changes(store, min_pct_change=args.min_pct)
    print(f"{'sku':<22} {'platform':<8} {'prev_vnd':>14} {'curr_vnd':>14} {'pct':>8}  dir")
    for e in events:
        print(
            f"{e.canonical_sku:<22} {e.platform.value:<8} "
            f"{e.previous_price_vnd:>14,} {e.current_price_vnd:>14,} "
            f"{e.pct_change:>+7.2f}%  {e.direction.value}"
        )
    print(f"\ntotal: {len(events)} price-change events")
    return 0


def cmd_arbitrage(args: argparse.Namespace) -> int:
    from multiprice.detectors import detect_arbitrage

    store = _load_store(Path(args.dataset))
    events = detect_arbitrage(store, min_spread_pct=args.min_spread)
    print(
        f"{'sku':<22} {'cheapest':<8} {'price':>14} {'expensive':<10} {'price':>14} {'spread':>8}"
    )
    for e in events:
        print(
            f"{e.canonical_sku:<22} {e.cheapest_platform.value:<8} "
            f"{e.cheapest_price_vnd:>14,} {e.most_expensive_platform.value:<10} "
            f"{e.most_expensive_price_vnd:>14,} {e.spread_pct:>7.2f}%"
        )
    print(f"\ntotal: {len(events)} arbitrage opportunities (≥ {args.min_spread}%)")
    return 0


def cmd_stockouts(args: argparse.Namespace) -> int:
    from multiprice.detectors import detect_stockouts

    store = _load_store(Path(args.dataset))
    events = detect_stockouts(store)
    print(f"{'sku':<22} {'platform':<8} {'observed_at'}")
    for e in events:
        print(f"{e.canonical_sku:<22} {e.platform.value:<8} {e.observed_at.isoformat()}")
    print(f"\ntotal: {len(events)} stockouts")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from multiprice.detectors import detect_arbitrage, detect_price_changes, detect_stockouts

    store = _load_store(Path(args.dataset))
    sys.stdout.write(
        json.dumps(
            {
                "n_observations": len(store),
                "n_skus": len(store.all_skus()),
                "n_series": store.n_series,
                "n_price_changes": len(detect_price_changes(store)),
                "n_arbitrage_opportunities": len(detect_arbitrage(store)),
                "n_stockouts": len(detect_stockouts(store)),
            },
            indent=2,
        )
    )
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="multiprice",
        description="Multi-platform price tracker for Shopee / Lazada / Tiki.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit synthetic mappings + observations")
    sim.add_argument("--skus", type=int, default=12)
    sim.add_argument("--snapshots", type=int, default=5)
    sim.add_argument("--interval", type=int, default=6, help="hours between snapshots")
    sim.add_argument(
        "--arbitrage", type=int, default=0, help="number of SKUs to inject arbitrage on"
    )
    sim.add_argument(
        "--stockouts", type=int, default=0, help="number of SKUs to inject stockouts on"
    )
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument(
        "--output", required=True, help="directory for mappings.jsonl + observations.jsonl"
    )
    sim.set_defaults(func=cmd_simulate)

    ch = sub.add_parser("changes", help="list price-change events")
    ch.add_argument("--dataset", required=True)
    ch.add_argument("--min-pct", dest="min_pct", type=float, default=0.0)
    ch.set_defaults(func=cmd_changes)

    arb = sub.add_parser("arbitrage", help="list cross-platform arbitrage opportunities")
    arb.add_argument("--dataset", required=True)
    arb.add_argument("--min-spread", dest="min_spread", type=float, default=10.0)
    arb.set_defaults(func=cmd_arbitrage)

    so = sub.add_parser("stockouts", help="list stockout events")
    so.add_argument("--dataset", required=True)
    so.set_defaults(func=cmd_stockouts)

    sm = sub.add_parser("summary", help="dump event counts as JSON")
    sm.add_argument("--dataset", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
