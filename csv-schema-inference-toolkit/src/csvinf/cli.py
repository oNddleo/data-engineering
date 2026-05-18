"""``csvinf`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from csvinf import __version__

    print(f"csv-schema-inference-toolkit {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from csvinf.simulator import generate

    body = generate(
        n_rows=args.rows,
        null_fraction=args.null_fraction,
        delimiter=args.delimiter,
        seed=args.seed,
    )
    if args.output:
        Path(args.output).write_text(body, encoding="utf-8")
        print(f"wrote {args.rows} rows to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(body)
    return 0


def cmd_infer(args: argparse.Namespace) -> int:
    from csvinf.infer import infer_schema
    from csvinf.io_jsonl import schema_to_dict

    text = Path(args.input).read_text(encoding="utf-8")
    schema = infer_schema(
        text,
        source_name=args.input,
        max_rows=args.max_rows if args.max_rows > 0 else None,
    )
    if args.output:
        Path(args.output).write_text(
            json.dumps(schema_to_dict(schema), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"wrote schema to {args.output}", file=sys.stderr)
    if args.show:
        print(f"source:    {schema.source_name}")
        print(f"delimiter: {schema.delimiter!r}")
        print(f"header:    {schema.has_header}")
        print(f"rows:      {schema.n_rows_scanned}")
        print(f"{'column':<24} {'type':<10} {'null%':>6} {'card':>6} {'fmt':<14}")
        for c in schema.columns:
            print(
                f"{c.name:<24} {c.type.value:<10} "
                f"{c.null_fraction * 100:>5.1f}% {c.cardinality:>6} "
                f"{c.detected_format:<14}"
            )
    return 0


def cmd_emit(args: argparse.Namespace) -> int:
    from csvinf.emit import emit_avro, emit_dataclass, emit_json_schema
    from csvinf.infer import infer_schema

    text = Path(args.input).read_text(encoding="utf-8")
    schema = infer_schema(text, source_name=args.input)
    if args.format == "avro":
        out = emit_avro(schema, record_name=args.name)
    elif args.format == "json-schema":
        out = emit_json_schema(schema, title=args.name)
    elif args.format == "dataclass":
        out = emit_dataclass(schema, class_name=args.name)
    else:
        raise SystemExit(f"unknown format: {args.format}")
    if args.output:
        Path(args.output).write_text(out + "\n", encoding="utf-8")
        print(f"wrote {args.format} schema to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
        sys.stdout.write("\n")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from collections import Counter

    from csvinf.infer import infer_schema

    text = Path(args.input).read_text(encoding="utf-8")
    schema = infer_schema(text, source_name=args.input)
    by_type: Counter[str] = Counter()
    for c in schema.columns:
        by_type[c.type.value] += 1
    nullable_cols = [c.name for c in schema.columns if c.nullable]
    high_card = [c.name for c in schema.columns if c.is_high_cardinality]
    payload = {
        "source": schema.source_name,
        "delimiter": schema.delimiter,
        "has_header": schema.has_header,
        "n_rows_scanned": schema.n_rows_scanned,
        "n_columns": len(schema.columns),
        "columns_by_type": dict(sorted(by_type.items())),
        "nullable_columns": nullable_cols,
        "high_cardinality_columns": high_card,
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="csvinf",
        description="Infer column types + emit Avro / JSON Schema / dataclass from CSV.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit a synthetic VN-flavoured CSV")
    sim.add_argument("--rows", type=int, default=100)
    sim.add_argument("--null-fraction", type=float, default=0.05)
    sim.add_argument("--delimiter", default=",")
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    inf = sub.add_parser("infer", help="infer the schema of a CSV file")
    inf.add_argument("--input", required=True)
    inf.add_argument("--output", default=None, help="write inferred schema as JSON to this path")
    inf.add_argument("--max-rows", type=int, default=0, help="limit scan to first N rows; 0 = all")
    inf.add_argument("--show", action="store_true", help="print a per-column summary to stdout")
    inf.set_defaults(func=cmd_infer)

    em = sub.add_parser("emit", help="emit a downstream schema from a CSV")
    em.add_argument("--input", required=True)
    em.add_argument("--format", choices=("avro", "json-schema", "dataclass"), required=True)
    em.add_argument("--name", default="Row", help="record/class name in the emitted schema")
    em.add_argument("--output", default=None)
    em.set_defaults(func=cmd_emit)

    sm = sub.add_parser("summary", help="JSON roll-up of inferred schema")
    sm.add_argument("--input", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
