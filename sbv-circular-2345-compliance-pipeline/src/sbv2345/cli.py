"""``sbv2345`` command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from sbv2345 import __version__

    print(f"sbv-circular-2345-compliance-pipeline {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from sbv2345.io_jsonl import dump_txns
    from sbv2345.simulator import generate

    bl = [a.strip() for a in (args.high_risk or "").split(",") if a.strip()]
    txns = generate(
        n_small=args.small,
        n_large=args.large,
        n_cumulative_pair=args.cumulative,
        n_cross_border=args.cross_border,
        n_high_risk_beneficiary=len(bl),
        high_risk_accounts=bl,
        seed=args.seed,
    )
    out = dump_txns(txns)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"wrote {len(txns)} transactions to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


def cmd_classify_and_seal(args: argparse.Namespace) -> int:
    from sbv2345.io_jsonl import dump_ledger, load_txns
    from sbv2345.ledger import AuditLedger
    from sbv2345.schema import VN_TZ
    from sbv2345.triggers import Classifier

    text = Path(args.input).read_text(encoding="utf-8")
    classifier = Classifier(
        high_risk_accounts=[a.strip() for a in (args.high_risk or "").split(",") if a.strip()]
    )
    ledger = AuditLedger()
    sealed_at = datetime.now(tz=VN_TZ)
    audited = 0
    for txn in load_txns(text):
        event = classifier.classify(txn)
        if event is not None:
            ledger.append(event, sealed_at=sealed_at)
            audited += 1
    out = dump_ledger(ledger)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(
            f"sealed {audited} audit-worthy events to {args.output} ({ledger.length} ledger rows)",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(out)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    from sbv2345.io_jsonl import load_ledger
    from sbv2345.ledger import TamperDetected

    text = Path(args.ledger).read_text(encoding="utf-8")
    try:
        load_ledger(text)
    except TamperDetected as e:
        print(f"TAMPER DETECTED at sequence {e.sequence_number}: {e.reason}", file=sys.stderr)
        return 1
    print("ledger chain OK", file=sys.stderr)
    return 0


def cmd_seal_day(args: argparse.Namespace) -> int:
    from sbv2345.io_jsonl import load_ledger
    from sbv2345.schema import VN_TZ

    text = Path(args.ledger).read_text(encoding="utf-8")
    ledger = load_ledger(text)
    day = date.fromisoformat(args.day)
    seal = ledger.seal_day(day, sealed_at=datetime.now(tz=VN_TZ))
    print(
        json.dumps(
            {
                "day": seal.day.isoformat(),
                "record_count": seal.record_count,
                "merkle_root": seal.merkle_root,
                "sealed_at": seal.sealed_at.isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from sbv2345.io_jsonl import load_ledger
    from sbv2345.reports import regulator_csv, summarise

    text = Path(args.ledger).read_text(encoding="utf-8")
    ledger = load_ledger(text)
    records = ledger.records()
    if args.format == "csv":
        sys.stdout.write(regulator_csv(records))
    else:
        s = summarise(records)
        sys.stdout.write(json.dumps(asdict(s), ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
    return 0


def cmd_retention(args: argparse.Namespace) -> int:
    from sbv2345.io_jsonl import load_ledger
    from sbv2345.retention import summarise

    text = Path(args.ledger).read_text(encoding="utf-8")
    ledger = load_ledger(text)
    today = date.fromisoformat(args.today) if args.today else date.today()
    summary = summarise(ledger, today=today)
    print(
        json.dumps(
            {
                "today": summary.today.isoformat(),
                "active": summary.active,
                "archive_eligible": summary.archive_eligible,
                "total": summary.total,
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="sbv2345",
        description="Tamper-evident audit-trail ledger for Decision 2345/QĐ-NHNN compliance.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit synthetic TransactionEvents as JSONL")
    sim.add_argument("--small", type=int, default=50)
    sim.add_argument("--large", type=int, default=5)
    sim.add_argument("--cumulative", type=int, default=2)
    sim.add_argument("--cross-border", dest="cross_border", type=int, default=2)
    sim.add_argument("--high-risk", dest="high_risk", default="", help="comma-list of accounts")
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    cs = sub.add_parser(
        "ingest", help="classify TransactionEvents and seal AuditEvents into the ledger"
    )
    cs.add_argument("--input", required=True)
    cs.add_argument("--high-risk", dest="high_risk", default="")
    cs.add_argument("--output", default=None)
    cs.set_defaults(func=cmd_classify_and_seal)

    vf = sub.add_parser("verify", help="walk the chain end-to-end and report any tamper")
    vf.add_argument("--ledger", required=True)
    vf.set_defaults(func=cmd_verify)

    sd = sub.add_parser("seal-day", help="compute the Merkle root for one calendar day")
    sd.add_argument("--ledger", required=True)
    sd.add_argument("--day", required=True, help="YYYY-MM-DD")
    sd.set_defaults(func=cmd_seal_day)

    rp = sub.add_parser("report", help="export the regulator CSV or a JSON summary")
    rp.add_argument("--ledger", required=True)
    rp.add_argument("--format", choices=["csv", "json"], default="json")
    rp.set_defaults(func=cmd_report)

    rt = sub.add_parser("retention", help="report retention-stage counts")
    rt.add_argument("--ledger", required=True)
    rt.add_argument("--today", default=None, help="YYYY-MM-DD; defaults to system today")
    rt.set_defaults(func=cmd_retention)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
