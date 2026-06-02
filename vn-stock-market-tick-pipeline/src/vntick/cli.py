"""``vntick`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from vntick import __version__

    print(f"vn-stock-market-tick-pipeline {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from vntick.io_jsonl import dump_symbols, dump_ticks
    from vntick.simulator import generate

    ceilings = tuple(args.ceiling.split(",")) if args.ceiling else ()
    symbols, ticks, prev_close = generate(
        n_ticks_per_symbol=args.ticks_per_symbol,
        seed=args.seed,
        ceiling_hit_codes=ceilings,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "symbols.jsonl").write_text(dump_symbols(symbols), encoding="utf-8")
    (out_dir / "ticks.jsonl").write_text(dump_ticks(ticks), encoding="utf-8")
    (out_dir / "previous_close.json").write_text(json.dumps(prev_close, indent=2), encoding="utf-8")
    print(
        f"wrote {len(symbols)} symbols + {len(ticks)} ticks to {out_dir}/",
        file=sys.stderr,
    )
    return 0


def cmd_resample(args: argparse.Namespace) -> int:
    from vntick.io_jsonl import dump_bars, load_ticks
    from vntick.resampler import resample

    ticks = list(load_ticks(Path(args.input).read_text(encoding="utf-8")))
    bars = resample(ticks, interval=args.interval)
    out = dump_bars(bars)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {len(bars)} bars to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


def cmd_indicators(args: argparse.Namespace) -> int:
    from vntick.indicators import ema, rsi, sma
    from vntick.io_jsonl import load_bars

    bars = list(load_bars(Path(args.bars).read_text(encoding="utf-8")))
    by_code: dict[str, list] = {}  # type: ignore[type-arg]
    for b in bars:
        by_code.setdefault(b.code, []).append(b)
    target = args.code
    if target not in by_code:
        print(f"unknown code {target}", file=sys.stderr)
        return 2
    group = by_code[target]
    sma_vals = sma(group, period=args.sma)
    ema_vals = ema(group, period=args.ema)
    rsi_vals = rsi(group, period=args.rsi)
    print(f"{'bar_start':<25} {'close':>9} {'sma':>9} {'ema':>9} {'rsi':>6}")
    for b, s, e, r in zip(group, sma_vals, ema_vals, rsi_vals, strict=True):
        sma_s = f"{s:>9.1f}" if s is not None else "       --"
        ema_s = f"{e:>9.1f}" if e is not None else "       --"
        rsi_s = f"{r:>6.1f}" if r is not None else "    --"
        print(f"{b.bar_start.isoformat():<25} {b.close_vnd:>9} {sma_s} {ema_s} {rsi_s}")
    return 0


def cmd_anomalies(args: argparse.Namespace) -> int:
    from vntick.anomaly import find_circuit_breaker_hits
    from vntick.io_jsonl import load_bars, load_symbols

    bars = list(load_bars(Path(args.bars).read_text(encoding="utf-8")))
    symbols = list(load_symbols(Path(args.symbols).read_text(encoding="utf-8")))
    prev_close: dict[str, int] = json.loads(Path(args.previous_close).read_text(encoding="utf-8"))
    exchanges = {s.code: s.exchange for s in symbols}
    hits = find_circuit_breaker_hits(bars, prev_close, exchanges)
    print(f"CIRCUIT-BREAKER HITS ({len(hits)}):")
    for h in hits[: args.n]:
        print(f"  {h.code:<6} {h.kind.value:<14} {h.detected_at.isoformat()} {h.detail}")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    from vntick.index import vn30_index, vn_index
    from vntick.io_jsonl import load_bars, load_symbols

    bars = list(load_bars(Path(args.bars).read_text(encoding="utf-8")))
    symbols_list = list(load_symbols(Path(args.symbols).read_text(encoding="utf-8")))
    symbols = {s.code: s for s in symbols_list}
    # Last bar's close per symbol.
    last_prices: dict[str, int] = {}
    for b in bars:
        last_prices[b.code] = b.close_vnd  # later bars overwrite earlier ones

    vni = vn_index(last_prices, symbols)
    vn30_codes = (
        set(args.vn30.split(","))
        if args.vn30
        else {"VIC", "VHM", "HPG", "VCB", "VNM", "FPT", "MSN", "MWG"}
    )
    vn30 = vn30_index(last_prices, symbols, vn30_codes)
    payload = {
        "vn_index_total_cap_vnd": int(vni),
        "vn30_total_cap_vnd": int(vn30),
        "vn30_codes": sorted(vn30_codes),
    }
    sys.stdout.write(json.dumps(payload, indent=2))
    sys.stdout.write("\n")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from vntick.io_jsonl import load_ticks

    ticks = list(load_ticks(Path(args.input).read_text(encoding="utf-8")))
    by_code: dict[str, list] = {}  # type: ignore[type-arg]
    for t in ticks:
        by_code.setdefault(t.code, []).append(t)
    payload = {
        "n_ticks": len(ticks),
        "n_symbols": len(by_code),
        "per_symbol": {
            code: {
                "n_ticks": len(group),
                "volume": sum(t.volume for t in group),
                "last_price": group[-1].price_vnd,
            }
            for code, group in sorted(by_code.items())
        },
    }
    sys.stdout.write(json.dumps(payload, indent=2))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="vntick",
        description="VN equity tick → OHLCV → indicators / anomalies / VN-Index pipeline.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="generate synthetic ticks for blue-chip universe")
    sim.add_argument("--ticks-per-symbol", type=int, default=200)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--ceiling", default="", help="comma-separated codes forced to ceiling")
    sim.add_argument("--out-dir", required=True)
    sim.set_defaults(func=cmd_simulate)

    rs = sub.add_parser("resample", help="tick stream → OHLCV bars")
    rs.add_argument("--input", required=True)
    rs.add_argument("--interval", default="5m", choices=["1m", "5m", "15m", "1h", "1d"])
    rs.add_argument("--output", default=None)
    rs.set_defaults(func=cmd_resample)

    ind = sub.add_parser("indicators", help="SMA / EMA / RSI for one symbol")
    ind.add_argument("--bars", required=True)
    ind.add_argument("--code", required=True)
    ind.add_argument("--sma", type=int, default=20)
    ind.add_argument("--ema", type=int, default=20)
    ind.add_argument("--rsi", type=int, default=14)
    ind.set_defaults(func=cmd_indicators)

    an = sub.add_parser("anomalies", help="circuit-breaker hits")
    an.add_argument("--bars", required=True)
    an.add_argument("--symbols", required=True)
    an.add_argument("--previous-close", required=True)
    an.add_argument("--n", type=int, default=20)
    an.set_defaults(func=cmd_anomalies)

    ix = sub.add_parser("index", help="VN-Index + VN30 market-cap totals")
    ix.add_argument("--bars", required=True)
    ix.add_argument("--symbols", required=True)
    ix.add_argument(
        "--vn30", default="", help="comma-separated VN30 codes; defaults to bundled list"
    )
    ix.set_defaults(func=cmd_index)

    sm = sub.add_parser("summary", help="JSON summary of a tick file")
    sm.add_argument("--input", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
