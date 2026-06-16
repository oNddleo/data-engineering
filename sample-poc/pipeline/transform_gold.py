"""Runner: silver -> gold marts. Reads silver (Polars), builds marts, writes gold."""
from __future__ import annotations

import settings
from io_iceberg import read_iceberg, write_iceberg
from iceberg_catalog import ensure_namespace, get_catalog
from transforms import gold


def main() -> None:
    ensure_namespace(get_catalog(), settings.NS_GOLD)

    customers = read_iceberg(f"{settings.NS_SILVER}.customers")
    products = read_iceberg(f"{settings.NS_SILVER}.products")
    orders = read_iceberg(f"{settings.NS_SILVER}.orders")
    order_items = read_iceberg(f"{settings.NS_SILVER}.order_items")

    marts = {
        "daily_revenue": gold.daily_revenue(orders, order_items),
        "revenue_by_category": gold.revenue_by_category(order_items, products),
        "top_customers": gold.top_customers(orders, order_items, customers),
        "order_status_funnel": gold.order_status_funnel(orders),
    }

    print("transform gold:")
    for name, df in marts.items():
        n = write_iceberg(df, f"{settings.NS_GOLD}.{name}", mode="overwrite")
        print(f"  {name:22s} {n:>6,} rows")


if __name__ == "__main__":
    main()
