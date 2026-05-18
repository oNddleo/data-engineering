"""``dqkit`` CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from dqkit import __version__
    from dqkit.runner import list_checks

    print(f"dwh-data-quality-toolkit {__version__}")
    print(f"checks ({len(list_checks())}): " + ", ".join(list_checks()))
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from dqkit.io_jsonl import dump_rows
    from dqkit.simulator import generate

    rows = generate(
        n_rows=args.rows,
        defect_fraction=args.defect_fraction,
        seed=args.seed,
    )
    out = dump_rows(rows)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {len(rows)} rows to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from dqkit.io_jsonl import (
        dump_results,
        dump_rows,
        load_rows,
        suite_from_json,
    )
    from dqkit.runner import quarantine_rows, render_summary, run_suite, summarise

    rows = load_rows(Path(args.input).read_text(encoding="utf-8"))
    suite = suite_from_json(Path(args.suite).read_text(encoding="utf-8"))
    results = run_suite(rows, suite)
    if args.results_output:
        Path(args.results_output).write_text(dump_results(results), encoding="utf-8")
        print(f"wrote {len(results)} check results to {args.results_output}", file=sys.stderr)
    if args.quarantine_dir:
        good, bad = quarantine_rows(rows, results)
        qd = Path(args.quarantine_dir)
        qd.mkdir(parents=True, exist_ok=True)
        (qd / "good.jsonl").write_text(dump_rows(good), encoding="utf-8")
        (qd / "bad.jsonl").write_text(dump_rows(bad), encoding="utf-8")
        print(f"quarantined {len(bad)} rows; kept {len(good)} good rows", file=sys.stderr)
    summary = summarise(results)
    sys.stdout.write(render_summary(summary))
    sys.stdout.write("\n")
    # Exit code matches CI conventions: 0 = all checks passed (or only WARNINGs);
    # 2 = at least one ERROR-severity check failed.
    by_sev = summary["by_severity"]
    return 2 if isinstance(by_sev, dict) and by_sev.get("ERROR", 0) > 0 else 0


def cmd_checks(_args: argparse.Namespace) -> int:
    from dqkit.runner import list_checks

    for name in list_checks():
        print(name)
    return 0


def cmd_make_suite(args: argparse.Namespace) -> int:
    """Emit a starter suite covering the bundled customer simulator schema."""
    from dqkit.io_jsonl import suite_to_json
    from dqkit.schema import CheckSpec, Severity, Suite

    suite = Suite(
        name="customer_default",
        specs=(
            CheckSpec(check="not_null", column="customer_id", severity=Severity.ERROR),
            CheckSpec(check="unique", column="customer_id", severity=Severity.ERROR),
            CheckSpec(check="cccd", column="cccd", severity=Severity.ERROR),
            CheckSpec(check="mst", column="mst", severity=Severity.ERROR),
            CheckSpec(check="vn_phone", column="phone", severity=Severity.WARNING),
            CheckSpec(check="vn_bank_account", column="bank_account", severity=Severity.ERROR),
            CheckSpec(check="vn_postal_code", column="postal_code", severity=Severity.WARNING),
            CheckSpec(
                check="in_set",
                column="tier",
                severity=Severity.ERROR,
                args={"allowed": "BASIC,STANDARD,PREFERRED,MALL"},
            ),
            CheckSpec(
                check="range_int",
                column="credit_limit_vnd",
                severity=Severity.ERROR,
                args={"lo": "0", "hi": "100000000"},
            ),
        ),
    )
    if args.output:
        Path(args.output).write_text(suite_to_json(suite), encoding="utf-8")
        print(f"wrote suite to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(suite_to_json(suite))
        sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="dqkit",
        description="Composable data-quality checks for VN data warehouses.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)
    sub.add_parser("checks", help="list registered check names").set_defaults(func=cmd_checks)

    sim = sub.add_parser("simulate", help="generate a synthetic customer rowset with defects")
    sim.add_argument("--rows", type=int, default=100)
    sim.add_argument("--defect-fraction", type=float, default=0.20)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    ms = sub.add_parser("make-suite", help="emit a starter suite for the customer schema")
    ms.add_argument("--output", default=None)
    ms.set_defaults(func=cmd_make_suite)

    run = sub.add_parser("run", help="run a suite against a JSONL rowset")
    run.add_argument("--input", required=True, help="rowset JSONL")
    run.add_argument("--suite", required=True, help="suite JSON")
    run.add_argument("--results-output", default=None, help="emit per-check results as JSONL")
    run.add_argument(
        "--quarantine-dir", default=None, help="split rows into good/bad on ERROR failures"
    )
    run.set_defaults(func=cmd_run)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
