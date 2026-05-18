"""``schemaev`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from schemaev import __version__

    print(f"schema-registry-evolution {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from schemaev.io_json import schema_to_json
    from schemaev.simulator import all_mutations, generate_pair

    if args.mutation not in all_mutations():
        print(
            f"unknown mutation {args.mutation!r}; choose from {all_mutations()}",
            file=sys.stderr,
        )
        return 2
    old, new = generate_pair(mutation=args.mutation, seed=args.seed)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "old.json").write_text(schema_to_json(old), encoding="utf-8")
    (out_dir / "new.json").write_text(schema_to_json(new), encoding="utf-8")
    print(
        f"wrote old + new schemas ({args.mutation}) to {out_dir}/",
        file=sys.stderr,
    )
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    from schemaev.diff import diff
    from schemaev.io_json import change_to_dict, schema_from_json

    old = schema_from_json(Path(args.old).read_text(encoding="utf-8"))
    new = schema_from_json(Path(args.new).read_text(encoding="utf-8"))
    changes = diff(old, new)
    payload = [change_to_dict(c) for c in changes]
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def cmd_compat(args: argparse.Namespace) -> int:
    from schemaev.compat import check
    from schemaev.io_json import (
        parse_compatibility,
        report_to_json,
        schema_from_json,
    )

    old = schema_from_json(Path(args.old).read_text(encoding="utf-8"))
    new = schema_from_json(Path(args.new).read_text(encoding="utf-8"))
    mode = parse_compatibility(args.mode)
    report = check(old, new, mode)
    if args.json:
        sys.stdout.write(report_to_json(report))
        sys.stdout.write("\n")
    else:
        verdict = "✓ COMPATIBLE" if report.is_compatible else "✗ INCOMPATIBLE"
        print(f"{verdict} under {report.mode.value}")
        print(f"\nBreaking ({len(report.breaking_changes)}):")
        for c in report.breaking_changes:
            print(f"  [{c.kind}] {c.field_name}: {c.detail}")
        print(f"\nSafe ({len(report.safe_changes)}):")
        for c in report.safe_changes:
            print(f"  [{c.kind}] {c.field_name}: {c.detail}")
    return 0 if report.is_compatible else 2


def cmd_bump(args: argparse.Namespace) -> int:
    from schemaev.diff import diff
    from schemaev.io_json import schema_from_json
    from schemaev.versioning import next_version, suggest_bump

    old = schema_from_json(Path(args.old).read_text(encoding="utf-8"))
    new = schema_from_json(Path(args.new).read_text(encoding="utf-8"))
    changes = diff(old, new)
    bump = suggest_bump(changes)
    payload = {
        "current_version": old.version,
        "suggested_bump": bump.value,
        "next_version": next_version(old.version, bump),
        "n_changes": len(changes),
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from schemaev.compat import check_backward, check_forward, check_full
    from schemaev.diff import diff
    from schemaev.io_json import schema_from_json
    from schemaev.versioning import next_version, suggest_bump

    old = schema_from_json(Path(args.old).read_text(encoding="utf-8"))
    new = schema_from_json(Path(args.new).read_text(encoding="utf-8"))
    changes = diff(old, new)
    bump = suggest_bump(changes)
    payload = {
        "old_version": old.version,
        "new_version": new.version,
        "n_changes": len(changes),
        "kinds": dict(sorted(_count_by_kind(changes).items())),
        "compatibility": {
            "BACKWARD": check_backward(old, new).is_compatible,
            "FORWARD": check_forward(old, new).is_compatible,
            "FULL": check_full(old, new).is_compatible,
        },
        "suggested_bump": bump.value,
        "suggested_next_version": next_version(old.version, bump),
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def _count_by_kind(changes: list) -> dict[str, int]:  # type: ignore[type-arg]
    from collections import Counter

    counts: Counter[str] = Counter()
    for c in changes:
        counts[c.kind] += 1
    return dict(counts)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="schemaev",
        description="JSON/Avro schema diff + compatibility checks + semver bump.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit (old, new) schemas exercising one mutation")
    sim.add_argument("--mutation", default="safe_add", help="see `schemaev simulate --help`")
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--out-dir", required=True)
    sim.set_defaults(func=cmd_simulate)

    df = sub.add_parser("diff", help="list FieldChanges between two schemas")
    df.add_argument("--old", required=True)
    df.add_argument("--new", required=True)
    df.set_defaults(func=cmd_diff)

    co = sub.add_parser("compat", help="check BACKWARD/FORWARD/FULL/NONE compat")
    co.add_argument("--old", required=True)
    co.add_argument("--new", required=True)
    co.add_argument("--mode", default="BACKWARD", choices=["BACKWARD", "FORWARD", "FULL", "NONE"])
    co.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of human-readable text",
    )
    co.set_defaults(func=cmd_compat)

    bp = sub.add_parser("bump", help="suggest semver bump from schema changes")
    bp.add_argument("--old", required=True)
    bp.add_argument("--new", required=True)
    bp.set_defaults(func=cmd_bump)

    sm = sub.add_parser("summary", help="JSON roll-up of diff + compat + bump")
    sm.add_argument("--old", required=True)
    sm.add_argument("--new", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
