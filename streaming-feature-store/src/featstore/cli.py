"""CLI entry-point for featstore."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from featstore.batch import BatchProcessor, DistributionStats
from featstore.registry import FeatureRegistry
from featstore.skew import SkewAlert, SkewDetector
from featstore.store import FeatureStore


def _cmd_ingest(args: argparse.Namespace) -> int:
    """featstore ingest --input FILE --entity-col E --ts-col T [--features F1,F2]"""
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".out.jsonl")

    # Auto-detect feature columns from first record if not specified
    feature_cols: list[str] = []
    if args.features:
        feature_cols = [f.strip() for f in args.features.split(",")]
    else:
        with input_path.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec: dict[str, Any] = json.loads(line)
                feature_cols = [k for k in rec if k not in (args.entity_col, args.ts_col)]
                break

    registry = FeatureRegistry()
    processor = BatchProcessor(registry)
    stats = processor.process(
        input_path=input_path,
        output_path=output_path,
        feature_cols=feature_cols,
        entity_col=args.entity_col,
        ts_col=args.ts_col,
    )
    print(f"Wrote {output_path}")
    for feat, ds in stats.items():
        print(f"  {feat}: count={ds.count} mean={ds.mean:.4f} std={ds.std:.4f}")
    if args.stats_output:
        processor.write_stats(stats, Path(args.stats_output))
        print(f"Stats written to {args.stats_output}")
    return 0


def _cmd_get(args: argparse.Namespace) -> int:
    """featstore get --entity E --feature F --store-jsonl FILE [--as-of TIMESTAMP]"""
    store = FeatureStore()
    store_path = Path(args.store_jsonl)
    if not store_path.exists():
        print(f"Store file not found: {store_path}", file=sys.stderr)
        return 1

    # Replay store from JSONL
    with store_path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec: dict[str, Any] = json.loads(line)
            entity = str(rec.get("entity_id", ""))
            ts_raw = rec.get("ts", "")
            ts = datetime.fromisoformat(str(ts_raw))
            for k, v in rec.items():
                if k in ("entity_id", "ts") or v is None:
                    continue
                store.put(entity, k, float(v) if isinstance(v, int | float) else v, ts)

    as_of: datetime | None = None
    if args.as_of:
        as_of = datetime.fromisoformat(args.as_of)
    val = store.get(args.entity, args.feature, as_of_ts=as_of)
    print(f"{args.entity}.{args.feature} @ {as_of or 'latest'} = {val}")
    return 0


def _cmd_scan(args: argparse.Namespace) -> int:
    """featstore scan --input FILE — print feature summary from JSONL."""
    input_path = Path(args.input)
    counts: dict[str, int] = {}
    total = 0
    with input_path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec: dict[str, Any] = json.loads(line)
            total += 1
            for k in rec:
                counts[k] = counts.get(k, 0) + 1
    print(f"Records: {total}")
    for col, cnt in sorted(counts.items()):
        print(f"  {col}: {cnt} values ({100*cnt//max(total,1)}% fill)")
    return 0


def _cmd_skew_check(args: argparse.Namespace) -> int:
    """featstore skew-check --batch-stats FILE --stream-stats FILE"""
    registry = FeatureRegistry()
    processor = BatchProcessor(registry)
    batch_stats: dict[str, DistributionStats] = processor.load_stats(Path(args.batch_stats))
    stream_stats: dict[str, DistributionStats] = processor.load_stats(Path(args.stream_stats))

    detector = SkewDetector(
        ks_threshold=float(args.ks_threshold),
        psi_threshold=float(args.psi_threshold),
    )
    exit_code = 0
    for feat in batch_stats:
        if feat not in stream_stats:
            print(f"  {feat}: missing in stream stats, skipping")
            continue
        try:
            report = detector.check(batch_stats[feat], stream_stats[feat])
            print(f"  {feat}: KS={report.ks_statistic:.4f} PSI={report.psi:.4f} OK")
        except SkewAlert as exc:
            print(f"  {feat}: KS={exc.report.ks_statistic:.4f} " f"PSI={exc.report.psi:.4f} ALERT")
            exit_code = 2
    return exit_code


def _cmd_stats(args: argparse.Namespace) -> int:
    """featstore stats --stats-file FILE — display saved distribution stats."""
    registry = FeatureRegistry()
    processor = BatchProcessor(registry)
    stats = processor.load_stats(Path(args.stats_file))
    for feat, ds in sorted(stats.items()):
        print(
            f"{feat}: count={ds.count} mean={ds.mean:.4f} "
            f"std={ds.std:.4f} min={ds.min_val:.4f} max={ds.max_val:.4f}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="featstore",
        description="Streaming feature store CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # ingest
    p_ingest = sub.add_parser("ingest", help="Process JSONL and compute stats")
    p_ingest.add_argument("--input", required=True)
    p_ingest.add_argument("--output", default="")
    p_ingest.add_argument("--entity-col", default="entity_id")
    p_ingest.add_argument("--ts-col", default="ts")
    p_ingest.add_argument("--features", default="")
    p_ingest.add_argument("--stats-output", default="")

    # get
    p_get = sub.add_parser("get", help="Look up a feature value from a store JSONL")
    p_get.add_argument("--entity", required=True)
    p_get.add_argument("--feature", required=True)
    p_get.add_argument("--store-jsonl", required=True)
    p_get.add_argument("--as-of", default="")

    # scan
    p_scan = sub.add_parser("scan", help="Scan JSONL and print column summary")
    p_scan.add_argument("--input", required=True)

    # skew-check
    p_skew = sub.add_parser("skew-check", help="Check distribution skew")
    p_skew.add_argument("--batch-stats", required=True)
    p_skew.add_argument("--stream-stats", required=True)
    p_skew.add_argument("--ks-threshold", default=0.1)
    p_skew.add_argument("--psi-threshold", default=0.2)

    # stats
    p_stats = sub.add_parser("stats", help="Display saved distribution stats")
    p_stats.add_argument("--stats-file", required=True)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    handlers = {
        "ingest": _cmd_ingest,
        "get": _cmd_get,
        "scan": _cmd_scan,
        "skew-check": _cmd_skew_check,
        "stats": _cmd_stats,
    }
    if args.command not in handlers:
        parser.print_help()
        sys.exit(1)
    sys.exit(handlers[args.command](args))
