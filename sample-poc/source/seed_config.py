"""Tunables + domain vocabulary for the synthetic e-commerce seeder.

Volumes are env-configurable so the seed stays laptop-friendly; defaults target
a < ~90s full load. Connection params default to the docker-compose source-db.
"""
from __future__ import annotations

import os

SEED = 42
BATCH = 10_000

# Baseline volumes (override via env).
N_CUSTOMERS = int(os.getenv("SEED_CUSTOMERS", "50000"))
N_PRODUCTS = int(os.getenv("SEED_PRODUCTS", "5000"))
N_ORDERS = int(os.getenv("SEED_ORDERS", "200000"))
MAX_ITEMS_PER_ORDER = int(os.getenv("SEED_MAX_ITEMS", "4"))

# Append-mode volumes.
APPEND_NEW_ORDERS = int(os.getenv("SEED_APPEND_ORDERS", "500"))
APPEND_UPDATED_ROWS = int(os.getenv("SEED_APPEND_UPDATES", "200"))

COUNTRIES = ["US", "VN", "DE", "JP", "BR", "IN", "GB", "FR", "AU", "CA"]
SEGMENTS = ["consumer", "smb", "enterprise"]
CATEGORIES = ["electronics", "books", "home", "fashion", "grocery", "toys", "sports"]
STATUSES = ["pending", "paid", "shipped", "delivered", "cancelled"]


def connection_params() -> dict:
    return {
        "host": os.getenv("SOURCE_DB_HOST", "localhost"),
        "port": int(os.getenv("SOURCE_DB_PORT", "5432")),
        "dbname": os.getenv("SOURCE_DB_NAME", "ecommerce"),
        "user": os.getenv("SOURCE_DB_USER", "source"),
        "password": os.getenv("SOURCE_DB_PASSWORD", "source"),
    }
