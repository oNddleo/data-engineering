"""``vnaddr`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from vnaddr import __version__

    print(f"vn-address-parser {__version__}")
    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    from vnaddr.io_jsonl import parsed_to_dict
    from vnaddr.parser import parse

    result = parse(args.text)
    if args.json:
        sys.stdout.write(
            json.dumps(parsed_to_dict(result), indent=2, ensure_ascii=False),
        )
        sys.stdout.write("\n")
    else:
        print(f"raw:       {result.raw_input}")
        print(f"street:    {result.street or '-'}")
        if result.ward is not None:
            print(
                f"ward:      {result.ward.matched_name or '?'} " f"({result.ward.kind.value})",
            )
        else:
            print("ward:      -")
        if result.district is not None:
            print(
                f"district:  {result.district.matched_name or '?'} "
                f"({result.district.kind.value})",
            )
        else:
            print("district:  -")
        if result.province is not None:
            print(
                f"province:  {result.province.matched_name or '?'} "
                f"({result.province.kind.value})",
            )
        else:
            print("province:  -")
        print(f"complete:  {result.is_complete}")
        print(f"normalised: {result.normalised}")
    return 0 if result.is_complete else 2


def cmd_batch(args: argparse.Namespace) -> int:
    from vnaddr.io_jsonl import dump_parsed
    from vnaddr.parser import parse

    lines = Path(args.input).read_text(encoding="utf-8").splitlines()
    parsed = [parse(line) for line in lines if line.strip()]
    text = dump_parsed(parsed)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"wrote {len(parsed)} parses to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    complete = sum(1 for p in parsed if p.is_complete)
    print(f"complete: {complete}/{len(parsed)}", file=sys.stderr)
    return 0


def cmd_normalize(args: argparse.Namespace) -> int:
    from vnaddr.normalize import normalise

    print(normalise(args.text))
    return 0


def cmd_list_units(args: argparse.Namespace) -> int:
    from vnaddr.schema import AdminLevel
    from vnaddr.units import by_level

    units = by_level(AdminLevel(args.level))
    for u in units:
        print(f"{u.code:<10} {u.name_vi}  ({u.name_en})")
    print(f"\n{len(units)} {args.level.lower()}(s) bundled", file=sys.stderr)
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from collections import Counter

    from vnaddr.parser import parse

    lines = Path(args.input).read_text(encoding="utf-8").splitlines()
    parsed = [parse(line) for line in lines if line.strip()]
    complete = sum(1 for p in parsed if p.is_complete)
    partial = sum(1 for p in parsed if p.is_partial and not p.is_complete)
    failures = sum(1 for p in parsed if not p.is_partial)
    by_kind: Counter[str] = Counter()
    for p in parsed:
        for t in (p.ward, p.district, p.province):
            if t is not None:
                by_kind[t.kind.value] += 1
    payload = {
        "n_inputs": len(parsed),
        "complete": complete,
        "partial": partial,
        "failed": failures,
        "completion_rate_pct": round(complete / len(parsed) * 100, 1) if parsed else 0.0,
        "matches_by_kind": dict(sorted(by_kind.items())),
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from vnaddr.simulator import NoiseLevel, generate

    lines = generate(
        n=args.n,
        noise=NoiseLevel(args.noise),
        seed=args.seed,
    )
    if args.output:
        Path(args.output).write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {len(lines)} addresses to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write("\n".join(lines) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="vnaddr",
        description="Parse VN postal addresses into 3-level admin structure.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    pa = sub.add_parser("parse", help="parse a single address")
    pa.add_argument("--text", required=True)
    pa.add_argument("--json", action="store_true", help="emit JSON")
    pa.set_defaults(func=cmd_parse)

    bt = sub.add_parser("batch", help="parse one address per line from a file")
    bt.add_argument("--input", required=True)
    bt.add_argument("--output", default=None)
    bt.set_defaults(func=cmd_batch)

    no = sub.add_parser("normalize", help="show the normalised form of an address")
    no.add_argument("--text", required=True)
    no.set_defaults(func=cmd_normalize)

    lu = sub.add_parser("list-units", help="list bundled administrative units")
    lu.add_argument("--level", choices=("PROVINCE", "DISTRICT", "WARD"), default="PROVINCE")
    lu.set_defaults(func=cmd_list_units)

    sm = sub.add_parser("summary", help="JSON roll-up of batch parsing")
    sm.add_argument("--input", required=True)
    sm.set_defaults(func=cmd_summary)

    sim = sub.add_parser("simulate", help="emit synthetic addresses")
    sim.add_argument("--n", type=int, default=100)
    sim.add_argument("--noise", choices=("CLEAN", "ABBREV", "FOLDED", "TYPO"), default="CLEAN")
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
