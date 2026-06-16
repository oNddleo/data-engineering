"""Runner: bronze -> silver. Reads bronze (Polars), cleans/dedups, writes silver."""
from __future__ import annotations

import settings
from io_iceberg import read_iceberg, write_iceberg
from iceberg_catalog import ensure_namespace, get_catalog
from transforms import silver

# table -> cleaning function
_CLEANERS = {
    "customers": silver.clean_customers,
    "products": silver.clean_products,
    "orders": silver.clean_orders,
    "order_items": silver.clean_order_items,
}


def main() -> None:
    ensure_namespace(get_catalog(), settings.NS_SILVER)
    print("transform silver:")
    for name, clean in _CLEANERS.items():
        df = read_iceberg(f"{settings.NS_BRONZE}.{name}")
        cleaned = clean(df)
        n = write_iceberg(cleaned, f"{settings.NS_SILVER}.{name}", mode="overwrite")
        print(f"  {name:12s} {df.height:>8,} bronze -> {n:>8,} silver")


if __name__ == "__main__":
    main()
