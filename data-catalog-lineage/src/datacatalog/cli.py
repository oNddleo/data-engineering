"""CLI for the data catalog."""

from __future__ import annotations

import argparse
import sys

from datacatalog.catalog import DataCatalog
from datacatalog.schema import Column, ColumnRef, DataSource, Table


def _seed_demo_catalog() -> DataCatalog:
    catalog = DataCatalog()
    # Raw layer
    raw = DataSource("raw", "Raw Layer")
    raw.tables = [
        Table(
            "customers",
            schema="raw",
            columns=[
                Column("customer_id", "int"),
                Column("email", "varchar"),
                Column("first_name", "varchar"),
                Column("last_name", "varchar"),
                Column("phone", "varchar"),
                Column("created_at", "timestamp"),
            ],
        ),
        Table(
            "orders",
            schema="raw",
            columns=[
                Column("order_id", "int"),
                Column("customer_id", "int"),
                Column("total_amount", "numeric"),
                Column("order_date", "date"),
            ],
        ),
    ]
    catalog.register_source(raw)

    # Staging layer
    stg = DataSource("staging", "Staging Layer")
    stg.tables = [
        Table(
            "stg_customers",
            schema="staging",
            columns=[
                Column("customer_id", "int"),
                Column("email", "varchar"),
                Column("full_name", "varchar"),
                Column("phone", "varchar"),
            ],
        ),
    ]
    catalog.register_source(stg)

    # Reporting layer
    rep = DataSource("reporting", "Reporting Layer")
    rep.tables = [
        Table(
            "customer_orders",
            schema="reporting",
            columns=[
                Column("customer_id", "int"),
                Column("email", "varchar"),
                Column("total_orders", "int"),
                Column("lifetime_value", "numeric"),
            ],
        ),
    ]
    catalog.register_source(rep)

    # Register lineage
    def ref(sid: str, sch: str, tbl: str, col: str) -> ColumnRef:
        return ColumnRef(sid, sch, tbl, col)

    catalog.register_job(
        "job_stg_customers",
        [
            (
                ref("raw", "raw", "customers", "customer_id"),
                ref("staging", "staging", "stg_customers", "customer_id"),
            ),
            (
                ref("raw", "raw", "customers", "email"),
                ref("staging", "staging", "stg_customers", "email"),
            ),
            (
                ref("raw", "raw", "customers", "phone"),
                ref("staging", "staging", "stg_customers", "phone"),
            ),
        ],
    )
    catalog.register_job(
        "job_reporting",
        [
            (
                ref("staging", "staging", "stg_customers", "customer_id"),
                ref("reporting", "reporting", "customer_orders", "customer_id"),
            ),
            (
                ref("staging", "staging", "stg_customers", "email"),
                ref("reporting", "reporting", "customer_orders", "email"),
            ),
        ],
    )
    return catalog


def _demo(args: argparse.Namespace) -> int:
    catalog = _seed_demo_catalog()
    pii = catalog.pii_report()

    if not args.quiet:
        print(f"Sources: {len(catalog.sources())}")
        print(f"PII columns: {len(pii)}")
        for ref, cat in pii:
            print(f"  {ref}  [{cat.value}]")

    if args.output:
        import io
        import pathlib

        from datacatalog.io_jsonl import write_sources as ws  # noqa: TCH001

        buf_sources = pathlib.Path(args.output)
        fh = io.StringIO()
        ws(catalog.sources(), fh)
        buf_sources.write_text(fh.getvalue())
        print(f"Wrote catalog → {args.output}")

    return 0


def _pii(args: argparse.Namespace) -> int:
    from datacatalog.pii import PIIDetector  # noqa: TCH001

    detector = PIIDetector()
    col_name = args.column
    samples = args.samples or []
    result = detector.detect(col_name, samples)
    print(f"{col_name}: {result.value}")
    return 0


def _lineage(args: argparse.Namespace) -> int:
    catalog = _seed_demo_catalog()
    parts = args.ref.split(".")
    if len(parts) != 4:
        print("error: ref must be source_id.schema.table.column", file=sys.stderr)
        return 1
    ref = ColumnRef(*parts)
    ups = catalog.upstream_of(ref)
    downs = catalog.downstream_of(ref)
    if not args.quiet:
        print(f"Upstream of {ref}:")
        for u in ups:
            print(f"  {u}")
        print(f"Downstream of {ref}:")
        for d in downs:
            print(f"  {d}")
    return 0


def _summary(args: argparse.Namespace) -> int:
    import pathlib

    path = pathlib.Path(args.catalog_file)
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 1

    from datacatalog.io_jsonl import read_sources  # noqa: TCH001

    with path.open() as fh:
        sources = read_sources(fh)

    total_tables = sum(len(s.tables) for s in sources)
    total_cols = sum(sum(len(t.columns) for t in s.tables) for s in sources)

    print(f"sources  : {len(sources)}")
    print(f"tables   : {total_tables}")
    print(f"columns  : {total_cols}")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="datacatalog",
        description="Data catalog with PII detection and lineage tracking",
    )
    sub = parser.add_subparsers(dest="command")

    p_demo = sub.add_parser("demo", help="Run demo catalog with 3-layer DWH")
    p_demo.add_argument("--output", help="Write catalog JSONL to this path")
    p_demo.add_argument("--quiet", action="store_true")

    p_pii = sub.add_parser("pii", help="Detect PII category for a column name")
    p_pii.add_argument("column", help="Column name to classify")
    p_pii.add_argument("--samples", nargs="*", help="Sample values")

    p_lin = sub.add_parser("lineage", help="Show lineage for a column reference")
    p_lin.add_argument("ref", help="ColumnRef: source_id.schema.table.column")
    p_lin.add_argument("--quiet", action="store_true")

    p_sum = sub.add_parser("summary", help="Summarise a catalog JSONL file")
    p_sum.add_argument("catalog_file")

    args = parser.parse_args(argv)
    dispatch = {
        "demo": _demo,
        "pii": _pii,
        "lineage": _lineage,
        "summary": _summary,
    }
    fn = dispatch.get(args.command or "")
    if fn is None:
        parser.print_help()
        return
    code = fn(args)
    if code:
        sys.exit(code)
