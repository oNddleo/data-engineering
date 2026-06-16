"""Seed the source OLTP Postgres with synthetic e-commerce data.

Modes:
  full    apply schema + bulk-seed a baseline (idempotent: skips if already seeded)
  append  insert a small batch of new orders + bump updated_at on some existing rows
          (this is the engine that proves incremental ELT in Phase 3)

Deterministic full load (Faker + random seeded) so demos reproduce after `make reset`.
Tunables live in seed_config.py.

Usage:
    python seed_source_data.py --mode full
    python seed_source_data.py --mode append
"""
from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta, timezone
import os

import psycopg2
from faker import Faker
from psycopg2.extras import execute_values

import seed_config as cfg


def connect():
    return psycopg2.connect(**cfg.connection_params())


def apply_schema(cur) -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "schema.sql"), "r", encoding="utf-8") as fh:
        cur.execute(fh.read())


def already_seeded(cur) -> bool:
    cur.execute("SELECT count(*) FROM customers")
    return cur.fetchone()[0] > 0


def _rand_ts(days_back: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(
        days=random.randint(0, days_back), seconds=random.randint(0, 86_400)
    )


def seed_full(conn) -> None:
    fake = Faker()
    Faker.seed(cfg.SEED)
    random.seed(cfg.SEED)
    cur = conn.cursor()

    apply_schema(cur)
    conn.commit()
    if already_seeded(cur):
        print("seed: already seeded — skipping (use --mode append or `make reset` first)")
        return

    print(f"seed: customers={cfg.N_CUSTOMERS} products={cfg.N_PRODUCTS} orders={cfg.N_ORDERS}")

    for start in range(0, cfg.N_CUSTOMERS, cfg.BATCH):
        n = min(start + cfg.BATCH, cfg.N_CUSTOMERS) - start
        rows = [
            (fake.name(), fake.unique.email(), random.choice(cfg.COUNTRIES),
             random.choice(cfg.SEGMENTS), _rand_ts(365))
            for _ in range(n)
        ]
        execute_values(
            cur, "INSERT INTO customers (name,email,country,segment,created_at) VALUES %s", rows
        )
    conn.commit()

    prod_rows = [
        (f"{fake.word().title()} {fake.word().title()}", random.choice(cfg.CATEGORIES),
         round(random.uniform(5, 800), 2), _rand_ts(365))
        for _ in range(cfg.N_PRODUCTS)
    ]
    execute_values(
        cur, "INSERT INTO products (name,category,price,created_at) VALUES %s", prod_rows
    )
    conn.commit()

    cur.execute("SELECT id, price FROM products")
    products = cur.fetchall()
    cur.execute("SELECT id FROM customers")
    customer_ids = [r[0] for r in cur.fetchall()]

    for start in range(0, cfg.N_ORDERS, cfg.BATCH):
        n = min(start + cfg.BATCH, cfg.N_ORDERS) - start
        order_rows = []
        for _ in range(n):
            ts = _rand_ts(90)
            order_rows.append((random.choice(customer_ids), random.choice(cfg.STATUSES), ts, ts))
        ids = execute_values(
            cur,
            "INSERT INTO orders (customer_id,status,order_ts,created_at) VALUES %s RETURNING id",
            order_rows, fetch=True,
        )
        item_rows = []
        for (oid,) in ids:
            for _ in range(random.randint(1, cfg.MAX_ITEMS_PER_ORDER)):
                pid, price = random.choice(products)
                item_rows.append((oid, pid, random.randint(1, 5), price))
        execute_values(
            cur,
            "INSERT INTO order_items (order_id,product_id,quantity,unit_price) VALUES %s",
            item_rows,
        )
        conn.commit()

    _print_counts(cur)


def seed_append(conn) -> None:
    """Insert new orders + bump updated_at on existing rows → proves incremental ELT."""
    random.seed()  # non-deterministic so repeated appends differ
    cur = conn.cursor()

    cur.execute("SELECT id, price FROM products")
    products = cur.fetchall()
    cur.execute("SELECT id FROM customers")
    customer_ids = [r[0] for r in cur.fetchall()]
    if not products or not customer_ids:
        raise SystemExit("append: no baseline data — run --mode full first")

    now = datetime.now(timezone.utc)
    order_rows = [
        (random.choice(customer_ids), random.choice(cfg.STATUSES), now, now, now)
        for _ in range(cfg.APPEND_NEW_ORDERS)
    ]
    ids = execute_values(
        cur,
        "INSERT INTO orders (customer_id,status,order_ts,created_at,updated_at) VALUES %s "
        "RETURNING id",
        order_rows, fetch=True,
    )
    item_rows = []
    for (oid,) in ids:
        for _ in range(random.randint(1, cfg.MAX_ITEMS_PER_ORDER)):
            pid, price = random.choice(products)
            item_rows.append((oid, pid, random.randint(1, 5), price, now))
    execute_values(
        cur,
        "INSERT INTO order_items (order_id,product_id,quantity,unit_price,updated_at) VALUES %s",
        item_rows,
    )

    cur.execute(
        "UPDATE orders SET status = %s, updated_at = now() "
        "WHERE id IN (SELECT id FROM orders ORDER BY random() LIMIT %s)",
        (random.choice(cfg.STATUSES), cfg.APPEND_UPDATED_ROWS),
    )
    conn.commit()
    print(f"append: +{cfg.APPEND_NEW_ORDERS} new orders, ~{cfg.APPEND_UPDATED_ROWS} rows touched")
    _print_counts(cur)


def _print_counts(cur) -> None:
    for t in ("customers", "products", "orders", "order_items"):
        cur.execute(f"SELECT count(*) FROM {t}")
        print(f"  {t:12s} {cur.fetchone()[0]:>10,}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("full", "append"), default="full")
    args = ap.parse_args()
    conn = connect()
    try:
        (seed_full if args.mode == "full" else seed_append)(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
