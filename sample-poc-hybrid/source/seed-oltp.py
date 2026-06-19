"""Seed the postgres-oltp `devices` database with synthetic dimension data.

Loads schema-oltp.sql, then truncates + inserts:
- 100 devices    (dev-0000 .. dev-0099) — pool the IoT simulator draws from.
- 20  locations  (Hanoi districts)
- 1:1 device→location assignments via `device_location` join.

Idempotent: runs DDL with CREATE TABLE IF NOT EXISTS, then TRUNCATE … RESTART
IDENTITY CASCADE before reseeding.

Usage:
    python seed-oltp.py \
        --host postgres-oltp --port 5432 \
        --db devices --user oltpuser --password oltppass
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import psycopg2  # type: ignore[import-untyped]
from faker import Faker  # type: ignore[import-untyped]
from psycopg2.extras import execute_values  # type: ignore[import-untyped]

LOG = logging.getLogger("seed-oltp")

HANOI_DISTRICTS = [
    "Ba Đình", "Hoàn Kiếm", "Hai Bà Trưng", "Đống Đa", "Tây Hồ",
    "Cầu Giấy", "Thanh Xuân", "Hoàng Mai", "Long Biên", "Nam Từ Liêm",
    "Bắc Từ Liêm", "Hà Đông", "Sơn Tây", "Mê Linh", "Thanh Trì",
    "Gia Lâm", "Đông Anh", "Sóc Sơn", "Thường Tín", "Phú Xuyên",
]

DEVICE_MODELS = ["AQ-Mini", "AQ-Pro", "VibroSense-100", "HydroLogger-S2"]
OWNER_ORGS = ["HanoiAirOps", "URENCO", "EVN-HN", "VinFast Mobility", "CityIoT Lab"]
FW_VERSIONS = ["1.0.0", "1.1.0", "1.2.3", "2.0.0"]


def load_schema(cur, ddl_path: Path) -> None:
    LOG.info("applying DDL from %s", ddl_path)
    cur.execute(ddl_path.read_text(encoding="utf-8"))


def truncate(cur) -> None:
    LOG.info("truncating device_location, devices, locations")
    cur.execute("TRUNCATE device_location, devices, locations RESTART IDENTITY CASCADE")


def seed_locations(cur, rng: random.Random, faker: Faker) -> list[int]:
    LAT_BASE, LON_BASE = 21.0285, 105.8542  # Hanoi centroid
    rows = []
    for idx, district in enumerate(HANOI_DISTRICTS, start=1):
        rows.append(
            (
                idx,
                "Hà Nội",
                district,
                round(LAT_BASE + rng.uniform(-0.15, 0.15), 6),
                round(LON_BASE + rng.uniform(-0.15, 0.15), 6),
            )
        )
    execute_values(
        cur,
        "INSERT INTO locations (location_id, city, district, lat, lon) VALUES %s",
        rows,
    )
    LOG.info("seeded %d locations", len(rows))
    return [r[0] for r in rows]


def seed_devices(cur, n: int, rng: random.Random) -> list[tuple[str, date]]:
    today = date.today()
    rows = []
    for i in range(n):
        device_id = f"dev-{i:04d}"
        install = today - timedelta(days=rng.randint(30, 720))
        rows.append(
            (
                device_id,
                rng.choice(DEVICE_MODELS),
                rng.choice(OWNER_ORGS),
                install,
                rng.choice(FW_VERSIONS),
            )
        )
    execute_values(
        cur,
        "INSERT INTO devices (device_id, model, owner_org, install_date, fw_version) VALUES %s",
        rows,
    )
    LOG.info("seeded %d devices", len(rows))
    return [(r[0], r[3]) for r in rows]


def seed_device_location(cur, devices: list[tuple[str, date]], location_ids: list[int], rng: random.Random) -> None:
    today = date.today()
    rows = []
    for device_id, install_date in devices:
        # Clamp assigned_from >= install_date so the FK timeline is consistent.
        earliest = install_date
        days_window = max((today - earliest).days, 1)
        rows.append(
            (
                device_id,
                rng.choice(location_ids),
                earliest + timedelta(days=rng.randint(0, days_window)),
            )
        )
    execute_values(
        cur,
        "INSERT INTO device_location (device_id, location_id, assigned_from) VALUES %s",
        rows,
    )
    LOG.info("seeded %d device-location assignments", len(rows))


def run(args: argparse.Namespace) -> int:
    rng = random.Random(args.seed)
    faker = Faker(["vi_VN"])
    Faker.seed(args.seed)

    ddl_path = Path(__file__).parent / "schema-oltp.sql"

    conn = psycopg2.connect(
        host=args.host, port=args.port,
        dbname=args.db, user=args.user, password=args.password,
    )
    try:
        with conn, conn.cursor() as cur:
            load_schema(cur, ddl_path)
            truncate(cur)
            location_ids = seed_locations(cur, rng, faker)
            devices = seed_devices(cur, args.devices, rng)
            seed_device_location(cur, devices, location_ids, rng)
        LOG.info("done.")
    finally:
        conn.close()
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed OLTP devices Postgres for the hybrid POC.")
    p.add_argument("--host", default=os.environ.get("PG_OLTP_HOST", "postgres-oltp"))
    p.add_argument("--port", type=int, default=int(os.environ.get("PG_OLTP_PORT", "5432")))
    p.add_argument("--db", default=os.environ.get("PG_OLTP_DB", "devices"))
    p.add_argument("--user", default=os.environ.get("PG_OLTP_USER", "oltpuser"))
    p.add_argument("--password", default=os.environ.get("PG_OLTP_PASSWORD", "oltppass"))
    p.add_argument("--devices", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--log-level", default="INFO")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
