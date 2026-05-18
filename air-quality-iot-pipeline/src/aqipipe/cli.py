"""``aqipipe`` CLI."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def cmd_info(_args: argparse.Namespace) -> int:
    from aqipipe import __version__

    print(f"air-quality-iot-pipeline {__version__}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from aqipipe.io_jsonl import dump_readings, dump_stations
    from aqipipe.simulator import generate

    stations, readings = generate(
        n_stations=args.stations,
        n_hours=args.hours,
        seed=args.seed,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "stations.jsonl").write_text(dump_stations(stations), encoding="utf-8")
    (out_dir / "readings.jsonl").write_text(dump_readings(readings), encoding="utf-8")
    print(
        f"wrote {len(stations)} stations + {len(readings)} readings to {out_dir}/",
        file=sys.stderr,
    )
    return 0


def cmd_aggregate(args: argparse.Namespace) -> int:
    from aqipipe.aggregate import aggregate
    from aqipipe.io_jsonl import dump_averages, load_readings

    readings = list(load_readings(Path(args.input).read_text(encoding="utf-8")))
    averages = aggregate(readings, window=args.window)
    out_text = dump_averages(averages)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
        print(
            f"wrote {len(averages)} {args.window} window averages to {args.output}",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(out_text)
    return 0


def cmd_aqi(args: argparse.Namespace) -> int:
    from aqipipe.aggregate import latest_per_station
    from aqipipe.io_jsonl import load_averages
    from aqipipe.qcvn import station_aqi

    averages = list(load_averages(Path(args.input).read_text(encoding="utf-8")))
    latest = latest_per_station(averages)
    out_rows = []
    for sid, polls in sorted(latest.items()):
        readings_x10 = {p: w.value_x10 for p, w in polls.items()}
        if not readings_x10:
            continue
        sa = station_aqi(sid, readings_x10)
        out_rows.append(sa)
    out_rows.sort(key=lambda sa: (-sa.aqi, sa.station_id))
    print(f"{'station':<10} {'aqi':>5} {'band':<22} {'dominant':<6}")
    for sa in out_rows[: args.n]:
        print(
            f"{sa.station_id:<10} {sa.aqi:>5} {sa.band.value:<22} "
            f"{sa.dominant_pollutant.value:<6}"
        )
    return 0


def cmd_alerts(args: argparse.Namespace) -> int:
    from aqipipe.aggregate import latest_per_station
    from aqipipe.alerts import band_distribution, find_public_alerts, find_sensitive_alerts
    from aqipipe.io_jsonl import load_averages
    from aqipipe.qcvn import AQIBand, station_aqi

    averages = list(load_averages(Path(args.input).read_text(encoding="utf-8")))
    latest = latest_per_station(averages)
    aqis = {
        sid: station_aqi(sid, {p: w.value_x10 for p, w in polls.items()})
        for sid, polls in latest.items()
        if polls
    }
    now = (
        datetime.fromisoformat(args.now)
        if args.now
        else max((a.window_end for a in averages), default=datetime.now().astimezone())
    )
    min_band = AQIBand(args.min_band)
    pub = find_public_alerts(aqis, now, min_band=min_band)
    sens = find_sensitive_alerts(aqis, now)
    dist = band_distribution(aqis)
    print(f"Band distribution ({len(aqis)} stations):")
    for band, n in dist.items():
        print(f"  {band.value:<22} {n:>5}")
    print(f"\nPUBLIC alerts ({len(pub)}):")
    for a in pub[: args.show]:
        print(f"  {a.station_id:<10} AQI {a.aqi:>3} ({a.band.value}) — {a.detail}")
    print(f"\nSENSITIVE-GROUP alerts ({len(sens)}):")
    for a in sens[: args.show]:
        print(f"  {a.station_id:<10} AQI {a.aqi:>3} ({a.band.value})")
    return 0


def cmd_quote(args: argparse.Namespace) -> int:
    """Quote AQI for one (pollutant, concentration) value."""
    from aqipipe.qcvn import aqi_for
    from aqipipe.schema import Pollutant

    pollutant = Pollutant(args.pollutant)
    aqi = aqi_for(pollutant, args.value_x10)
    payload = {
        "pollutant": pollutant.value,
        "value_x10": aqi.value_x10,
        "aqi": aqi.aqi,
        "band": aqi.band.value,
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    from aqipipe.io_jsonl import load_readings

    readings = list(load_readings(Path(args.input).read_text(encoding="utf-8")))
    by_station: dict[str, int] = {}
    by_pollutant: dict[str, int] = {}
    by_quality: dict[str, int] = {}
    for r in readings:
        by_station[r.station_id] = by_station.get(r.station_id, 0) + 1
        by_pollutant[r.pollutant.value] = by_pollutant.get(r.pollutant.value, 0) + 1
        by_quality[r.quality] = by_quality.get(r.quality, 0) + 1
    payload = {
        "n_readings": len(readings),
        "n_stations": len(by_station),
        "by_pollutant": dict(sorted(by_pollutant.items())),
        "by_quality": dict(sorted(by_quality.items())),
    }
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="aqipipe",
        description="VN air-quality pipeline — readings → averages → QCVN-05 AQI + health alerts.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    sim = sub.add_parser("simulate", help="emit synthetic stations + readings")
    sim.add_argument("--stations", type=int, default=10)
    sim.add_argument("--hours", type=int, default=24)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--out-dir", required=True)
    sim.set_defaults(func=cmd_simulate)

    ag = sub.add_parser("aggregate", help="bucket readings into 1h / 8h / 24h averages")
    ag.add_argument("--input", required=True, help="readings.jsonl")
    ag.add_argument("--window", default="1h", choices=["1h", "8h", "24h"])
    ag.add_argument("--output", default=None)
    ag.set_defaults(func=cmd_aggregate)

    aq = sub.add_parser("aqi", help="compute station AQI from window averages")
    aq.add_argument("--input", required=True, help="averages.jsonl")
    aq.add_argument("--n", type=int, default=20)
    aq.set_defaults(func=cmd_aqi)

    al = sub.add_parser("alerts", help="health-warning alerts from station AQIs")
    al.add_argument("--input", required=True, help="averages.jsonl")
    al.add_argument(
        "--min-band",
        default="UNHEALTHY_SENSITIVE",
        choices=[
            "GOOD",
            "MODERATE",
            "UNHEALTHY_SENSITIVE",
            "UNHEALTHY",
            "VERY_UNHEALTHY",
            "HAZARDOUS",
        ],
    )
    al.add_argument("--now", default=None, help="ISO timestamp; defaults to latest window end")
    al.add_argument("--show", type=int, default=5)
    al.set_defaults(func=cmd_alerts)

    qt = sub.add_parser("quote", help="what-if AQI for (pollutant, value_x10)")
    qt.add_argument("pollutant", choices=["PM25", "PM10", "NO2", "SO2", "O3", "CO"])
    qt.add_argument("value_x10", type=int)
    qt.set_defaults(func=cmd_quote)

    sm = sub.add_parser("summary", help="JSON summary of a readings file")
    sm.add_argument("--input", required=True)
    sm.set_defaults(func=cmd_summary)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
