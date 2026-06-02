"""``vnprop`` CLI — parse, normalize, simulate VN property listings."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from vnprop import __version__

    print(f"vn-property-listing-normalizer {__version__}")
    return 0


def cmd_parse_price(args: argparse.Namespace) -> int:
    from vnprop.price import parse_price_vnd

    vnd = parse_price_vnd(args.text)
    payload = {"input": args.text, "value_vnd": vnd}
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return 0


def cmd_parse_area(args: argparse.Namespace) -> int:
    from vnprop.area import parse_area_m2

    m2 = parse_area_m2(args.text)
    payload = {"input": args.text, "area_m2": m2}
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return 0


def cmd_normalize(args: argparse.Namespace) -> int:
    """Normalize raw JSONL listings into structured Listings."""
    from vnprop.io_jsonl import dump_listings, load_raw
    from vnprop.normalizer import normalize

    raw = load_raw(Path(args.input).read_text(encoding="utf-8"))
    out = [normalize(r) for r in raw]
    if args.output:
        Path(args.output).write_text(dump_listings(out), encoding="utf-8")
        print(f"wrote {len(out)} listings to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(dump_listings(out))
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from vnprop.io_jsonl import dump_raw
    from vnprop.simulator import generate

    raw = generate(n=args.n, seed=args.seed)
    if args.output:
        Path(args.output).write_text(dump_raw(raw), encoding="utf-8")
        print(f"wrote {len(raw)} raw listings to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(dump_raw(raw))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="vnprop",
        description="VN property-listing normalizer.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    pp = sub.add_parser("price", help="parse a VN price string")
    pp.add_argument("text")
    pp.set_defaults(func=cmd_parse_price)

    pa = sub.add_parser("area", help="parse a VN area string")
    pa.add_argument("text")
    pa.set_defaults(func=cmd_parse_area)

    n = sub.add_parser("normalize", help="normalize a JSONL of raw listings")
    n.add_argument("--input", required=True)
    n.add_argument("--output", default=None)
    n.set_defaults(func=cmd_normalize)

    sim = sub.add_parser("simulate", help="emit synthetic raw listings")
    sim.add_argument("--n", type=int, default=20)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
