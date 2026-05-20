"""``vnstock`` CLI — exchanges, tickers, pricing, simulate, anomalies."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from vnstock import __version__

    print(f"vn-stock-ticker-pipeline {__version__}")
    return 0


def cmd_exchanges(_args: argparse.Namespace) -> int:
    """List bundled VN exchanges with their trading rules."""
    from vnstock.exchanges import all_exchanges

    print(
        f"{'CODE':<6} {'NAME':<45} {'BAND%':>7} {'IPO%':>6} " f"{'LOT':>4} {'TICK':>8}",
    )
    for p in all_exchanges():
        tick = "tiered" if p.flat_tick_vnd == 0 else str(p.flat_tick_vnd)
        print(
            f"{p.code.value:<6} {p.name_en[:45]:<45} "
            f"{p.price_band_bps / 100:>6.1f}% {p.ipo_band_bps / 100:>5.1f}% "
            f"{p.lot_size:>4} {tick:>8}",
        )
    return 0


def cmd_tickers(args: argparse.Namespace) -> int:
    """List bundled tickers, optionally filtered by exchange."""
    from vnstock.schema import Exchange
    from vnstock.tickers import all_tickers, tickers_on

    tickers = tickers_on(Exchange(args.exchange.upper())) if args.exchange else all_tickers()
    print(f"{'SYM':<6} {'EXCH':<6} {'NAME':<45} {'INDUSTRY':<25}")
    for t in tickers:
        print(
            f"{t.symbol:<6} {t.exchange.value:<6} " f"{t.name_en[:45]:<45} {t.industry[:25]:<25}",
        )
    return 0


def cmd_band(args: argparse.Namespace) -> int:
    """Compute today's ceiling / floor for a reference price."""
    from vnstock.pricing import ceiling_floor
    from vnstock.schema import Exchange

    exchange = Exchange(args.exchange.upper())
    ceiling, floor = ceiling_floor(
        args.reference,
        exchange,
        is_ipo_day=args.ipo,
    )
    payload = {
        "exchange": exchange.value,
        "reference_price_vnd": args.reference,
        "is_ipo_day": args.ipo,
        "ceiling_vnd": ceiling,
        "floor_vnd": floor,
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0


def cmd_tick(args: argparse.Namespace) -> int:
    """Look up the applicable tick size at a given price."""
    from vnstock.pricing import tick_size
    from vnstock.schema import Exchange

    exchange = Exchange(args.exchange.upper())
    tick = tick_size(args.price, exchange)
    payload = {
        "exchange": exchange.value,
        "price_vnd": args.price,
        "tick_vnd": tick,
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from vnstock.io_jsonl import dump_bars
    from vnstock.simulator import generate

    bars = generate(
        n_tickers=args.tickers,
        n_days=args.days,
        seed=args.seed,
    )
    if args.output:
        Path(args.output).write_text(dump_bars(bars), encoding="utf-8")
        print(f"wrote {len(bars)} bars to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(dump_bars(bars))
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from vnstock.aggregator import aggregate_ticker_stats
    from vnstock.io_jsonl import dump_stats, load_bars

    bars = load_bars(Path(args.input).read_text(encoding="utf-8"))
    stats = aggregate_ticker_stats(bars)
    if args.output:
        Path(args.output).write_text(dump_stats(stats), encoding="utf-8")
        print(f"wrote {len(stats)} stats to {args.output}", file=sys.stderr)
    if args.show:
        print(
            f"{'SYM':<6} {'EXCH':<6} {'#bars':>5} {'HWM':>10} "
            f"{'LWM':>10} {'avg_vol':>10} {'change':>10}",
        )
        for s in stats[: args.show]:
            print(
                f"{s.symbol:<6} {s.exchange.value:<6} "
                f"{s.n_bars:>5} {s.high_water_mark_vnd:>10,} "
                f"{s.low_water_mark_vnd:>10,} {s.avg_volume:>10,} "
                f"{s.period_change_vnd:>10,}",
            )
    return 0


def cmd_anomaly(args: argparse.Namespace) -> int:
    from vnstock.anomaly import (
        find_band_breaches,
        find_price_gaps,
        find_volume_spikes,
    )
    from vnstock.io_jsonl import load_bars

    bars = load_bars(Path(args.input).read_text(encoding="utf-8"))
    breaches = find_band_breaches(bars)
    spikes = find_volume_spikes(bars)
    gaps = find_price_gaps(bars)
    print(f"PRICE_BAND_BREACH ({len(breaches)}):")
    for f in breaches[: args.show]:
        print(f"  {f.symbol:<6} {f.exchange.value:<6} {f.date.isoformat()} {f.detail}")
    print(f"VOLUME_SPIKE ({len(spikes)}):")
    for f in spikes[: args.show]:
        print(f"  {f.symbol:<6} {f.exchange.value:<6} {f.date.isoformat()} {f.detail}")
    print(f"PRICE_GAP ({len(gaps)}):")
    for f in gaps[: args.show]:
        print(f"  {f.symbol:<6} {f.exchange.value:<6} {f.date.isoformat()} {f.detail}")
    return 0 if not (breaches or spikes or gaps) else 2


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="vnstock",
        description="VN stock exchange pipeline — OHLC, pricing rules, anomalies.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)
    sub.add_parser("exchanges").set_defaults(func=cmd_exchanges)

    tk = sub.add_parser("tickers", help="list bundled tickers")
    tk.add_argument("--exchange", default=None)
    tk.set_defaults(func=cmd_tickers)

    bd = sub.add_parser("band", help="compute today's ceiling/floor")
    bd.add_argument("--reference", type=int, required=True)
    bd.add_argument("--exchange", required=True)
    bd.add_argument("--ipo", action="store_true")
    bd.set_defaults(func=cmd_band)

    tc = sub.add_parser("tick", help="lookup tick size at a price")
    tc.add_argument("--price", type=int, required=True)
    tc.add_argument("--exchange", required=True)
    tc.set_defaults(func=cmd_tick)

    sim = sub.add_parser("simulate", help="emit a synthetic OHLC stream")
    sim.add_argument("--tickers", type=int, default=20)
    sim.add_argument("--days", type=int, default=30)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    sm = sub.add_parser("summary", help="per-ticker rollup")
    sm.add_argument("--input", required=True)
    sm.add_argument("--output", default=None)
    sm.add_argument("--show", type=int, default=10)
    sm.set_defaults(func=cmd_summary)

    an = sub.add_parser("anomaly", help="detect band breach / volume spike / gap")
    an.add_argument("--input", required=True)
    an.add_argument("--show", type=int, default=5)
    an.set_defaults(func=cmd_anomaly)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
