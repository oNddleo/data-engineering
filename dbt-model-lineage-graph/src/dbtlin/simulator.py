"""Seeded synthetic dbt project for testing.

Generates a realistic staging → intermediate → mart layered project
shape with Vietnamese-themed table names:

```
sources           staging              intermediate         mart
shopee.raw_orders  → stg_orders     → int_order_items     → fact_revenue_daily
shopee.raw_users   → stg_users      → int_user_first_buy   → dim_customer
shopee.raw_returns → stg_returns    → int_return_summary  → fact_returns_daily
```

Each model is a dbt SQL file with realistic ``{{ ref() }}`` and
``{{ source() }}`` calls. ``inject_cycle=True`` adds a deliberate
upstream loop so cycle-detection tests can fire.
"""

from __future__ import annotations

import random


def _staging_sql(stg_name: str, source_schema: str, source_table: str) -> str:
    return (
        f"-- staging model {stg_name}\n"
        f"with src as (\n"
        f"  select * from {{{{ source('{source_schema}', '{source_table}') }}}}\n"
        f")\n"
        f"select * from src\n"
    )


def _intermediate_sql(int_name: str, stg_refs: list[str]) -> str:
    sql = f"-- intermediate model {int_name}\n"
    for i, ref in enumerate(stg_refs):
        sql += f"with t{i} as (select * from {{{{ ref('{ref}') }}}})\n"
    sql += "select * from " + ", ".join(f"t{i}" for i in range(len(stg_refs))) + "\n"
    return sql


def _mart_sql(mart_name: str, int_refs: list[str]) -> str:
    sql = f"-- mart model {mart_name}\n"
    sql += "select\n"
    for i, ref in enumerate(int_refs):
        sql += f"  -- pulled from {ref}\n"
        sql += f"  t{i}.*\n"
        if i < len(int_refs) - 1:
            sql = sql.rstrip("\n") + ",\n"
    sql += "from " + ", ".join(f"{{{{ ref('{r}') }}}} t{i}" for i, r in enumerate(int_refs)) + "\n"
    return sql


def generate(*, seed: int = 0, inject_cycle: bool = False) -> dict[str, str]:
    """Generate a small realistic dbt project as ``{model_name: sql}``.

    Deterministic for a given seed. ``inject_cycle=True`` adds a
    ``fact_revenue_daily`` → ``int_revenue_loop`` →
    ``fact_revenue_daily`` self-reference for cycle-detection tests.
    """
    rng = random.Random(seed)

    models: dict[str, str] = {}

    # Staging
    models["stg_orders"] = _staging_sql("stg_orders", "shopee", "raw_orders")
    models["stg_users"] = _staging_sql("stg_users", "shopee", "raw_users")
    models["stg_returns"] = _staging_sql("stg_returns", "shopee", "raw_returns")
    models["stg_inventory"] = _staging_sql("stg_inventory", "shopee", "raw_inventory")

    # Intermediate
    models["int_order_items"] = _intermediate_sql(
        "int_order_items", ["stg_orders", "stg_inventory"]
    )
    models["int_user_first_buy"] = _intermediate_sql(
        "int_user_first_buy", ["stg_orders", "stg_users"]
    )
    models["int_return_summary"] = _intermediate_sql(
        "int_return_summary", ["stg_returns", "stg_orders"]
    )

    # Mart
    models["fact_revenue_daily"] = _mart_sql(
        "fact_revenue_daily", ["int_order_items", "int_user_first_buy"]
    )
    models["fact_returns_daily"] = _mart_sql("fact_returns_daily", ["int_return_summary"])
    models["dim_customer"] = _mart_sql("dim_customer", ["int_user_first_buy"])

    # A jitter model that picks one random staging dep — exercises the
    # deterministic-output property tests.
    options = ["stg_orders", "stg_users"]
    pick = rng.choice(options)
    models["dim_customer_extras"] = _mart_sql("dim_customer_extras", [pick])

    if inject_cycle:
        # Insert a small loop: fact_revenue_daily ← int_revenue_loop ← fact_revenue_daily.
        models["int_revenue_loop"] = (
            "-- intentional loop\n" "select * from {{ ref('fact_revenue_daily') }}\n"
        )
        models["fact_revenue_daily"] = (
            models["fact_revenue_daily"].rstrip("\n")
            + ",\n  (select sum(x) from {{ ref('int_revenue_loop') }})\n"
        )

    return models


__all__ = ["generate"]
