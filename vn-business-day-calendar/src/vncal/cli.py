"""``vncal`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from vncal import __version__

    print(f"vn-business-day-calendar {__version__}")
    return 0


def cmd_holidays(args: argparse.Namespace) -> int:
    from vncal.holidays import build_year, build_years
    from vncal.io_jsonl import dump_holidays

    holidays = build_years(args.year, args.year_to) if args.year_to else build_year(args.year)
    if args.output:
        Path(args.output).write_text(dump_holidays(holidays), encoding="utf-8")
        print(f"wrote {len(holidays)} holidays to {args.output}", file=sys.stderr)
    else:
        print(f"{'date':<12} {'day':<3} {'kind':<13} name")
        for h in holidays:
            print(
                f"{h.date.isoformat():<12} {h.date.strftime('%a'):<3} "
                f"{h.kind.value:<13} {h.name_vi}"
            )
    return 0


def cmd_is_business_day(args: argparse.Namespace) -> int:
    from vncal.calendar_ops import is_business_day

    d = date.fromisoformat(args.date)
    answer = is_business_day(d)
    print(
        f"{d.isoformat()} ({d.strftime('%A')}): "
        f"{'business day' if answer else 'NOT a business day'}"
    )
    return 0 if answer else 1


def cmd_add(args: argparse.Namespace) -> int:
    from vncal.calendar_ops import add_business_days

    d = date.fromisoformat(args.date)
    out = add_business_days(d, args.days)
    print(out.isoformat())
    return 0


def cmd_between(args: argparse.Namespace) -> int:
    from vncal.calendar_ops import business_days_between

    a = date.fromisoformat(args.start)
    b = date.fromisoformat(args.end)
    n = business_days_between(a, b)
    print(n)
    return 0


def cmd_fiscal_year(args: argparse.Namespace) -> int:
    from vncal.fiscal import fiscal_year_for

    d = date.fromisoformat(args.date)
    fy = fiscal_year_for(d, april_march=args.april_march)
    print(f"{fy.label}: {fy.start_date} – {fy.end_date} ({fy.days_in_year()} days)")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """Compute a JSON roll-up of the calendar across one year."""
    from collections import Counter

    from vncal.calendar_ops import is_business_day
    from vncal.holidays import build_year

    holidays = build_year(args.year)
    by_kind: Counter[str] = Counter()
    for h in holidays:
        by_kind[h.kind.value] += 1
    # Count business / non-business days across the year.
    first = date(args.year, 1, 1)
    n_days = (date(args.year + 1, 1, 1) - first).days
    n_business = 0
    holiday_set = {h.date for h in holidays}
    for offset in range(n_days):
        d = first + timedelta(days=offset)
        if is_business_day(d, holidays=holiday_set):
            n_business += 1
    payload = {
        "year": args.year,
        "n_holidays": len(holidays),
        "n_business_days": n_business,
        "n_calendar_days": n_days,
        "holidays_by_kind": dict(sorted(by_kind.items())),
        "tet_eve": holidays[1].date.isoformat()
        if len(holidays) > 1 and holidays[1].kind.value == "TET"
        else None,
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="vncal",
        description="Vietnamese public-holiday + working-day calendar.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    hol = sub.add_parser("holidays", help="list public holidays for a year (or range)")
    hol.add_argument("--year", type=int, required=True)
    hol.add_argument(
        "--year-to", type=int, default=None, help="if given, list [year, year_to] inclusive"
    )
    hol.add_argument("--output", default=None, help="JSONL output file")
    hol.set_defaults(func=cmd_holidays)

    isd = sub.add_parser("is-business-day", help="exit 0 if date is a business day, else 1")
    isd.add_argument("--date", required=True, help="ISO date YYYY-MM-DD")
    isd.set_defaults(func=cmd_is_business_day)

    add = sub.add_parser("add", help="add (signed) business days to a date")
    add.add_argument("--date", required=True)
    add.add_argument("--days", type=int, required=True)
    add.set_defaults(func=cmd_add)

    bet = sub.add_parser("between", help="business days in [start, end)")
    bet.add_argument("--start", required=True)
    bet.add_argument("--end", required=True)
    bet.set_defaults(func=cmd_between)

    fy = sub.add_parser("fiscal-year", help="resolve fiscal year for a date")
    fy.add_argument("--date", required=True)
    fy.add_argument(
        "--april-march", action="store_true", help="use April-March fiscal year convention"
    )
    fy.set_defaults(func=cmd_fiscal_year)

    sm = sub.add_parser("summary", help="JSON roll-up of a calendar year")
    sm.add_argument("--year", type=int, required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
