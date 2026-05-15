"""In-memory product + shop warehouse with append-only price history.

Three tables:

* :class:`ProductFacts` — one current row per ``(item_id, shop_id)``
  pair. Replaces on insert iff the new snapshot is later than the
  stored one. Late-arriving older snapshots are ignored.
* :class:`PriceHistory` — append-only sequence of every observed
  price for each ``(item_id, shop_id)``. Time-sorted on read.
* :class:`ShopFacts` — one current row per ``shop_id``, same
  late-arrival policy as ProductFacts.

The warehouse is intentionally narrow — it provides indexed lookups
and time-window queries, and that's it. Aggregations live in
:mod:`shopeedw.aggregations` because they compose multiple table
reads.
"""

from __future__ import annotations

import bisect
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime

    from shopeedw.schema import ShopeeProduct, ShopeeShop


class ProductFacts:
    """Latest-snapshot table for products. Composite key: (item_id, shop_id)."""

    def __init__(self) -> None:
        self._rows: dict[tuple[int, int], ShopeeProduct] = {}

    def __len__(self) -> int:
        return len(self._rows)

    def upsert(self, product: ShopeeProduct) -> bool:
        """Insert or replace iff this snapshot is newer.

        Returns True if the row was inserted or replaced, False if
        the existing row was newer (late-arriving snapshot dropped).
        """
        key = (product.item_id, product.shop_id)
        existing = self._rows.get(key)
        if existing is not None and existing.fetched_at >= product.fetched_at:
            return False
        self._rows[key] = product
        return True

    def get(self, item_id: int, shop_id: int) -> ShopeeProduct | None:
        return self._rows.get((item_id, shop_id))

    def all(self) -> list[ShopeeProduct]:
        return list(self._rows.values())

    def by_category(self, category_key: str) -> list[ShopeeProduct]:
        return [p for p in self._rows.values() if p.category_key == category_key]

    def by_shop(self, shop_id: int) -> list[ShopeeProduct]:
        return [p for p in self._rows.values() if p.shop_id == shop_id]


class ShopFacts:
    """Latest-snapshot table for shops. Key: shop_id."""

    def __init__(self) -> None:
        self._rows: dict[int, ShopeeShop] = {}

    def __len__(self) -> int:
        return len(self._rows)

    def upsert(self, shop: ShopeeShop) -> bool:
        existing = self._rows.get(shop.shop_id)
        if existing is not None and existing.fetched_at >= shop.fetched_at:
            return False
        self._rows[shop.shop_id] = shop
        return True

    def get(self, shop_id: int) -> ShopeeShop | None:
        return self._rows.get(shop_id)

    def all(self) -> list[ShopeeShop]:
        return list(self._rows.values())


class PriceHistory:
    """Append-only price-history table per ``(item_id, shop_id)``."""

    def __init__(self) -> None:
        self._series: dict[tuple[int, int], list[tuple[datetime, int]]] = {}

    def __len__(self) -> int:
        return sum(len(v) for v in self._series.values())

    def append(self, product: ShopeeProduct) -> None:
        key = (product.item_id, product.shop_id)
        s = self._series.setdefault(key, [])
        # bisect keeps the list sorted by time; duplicates allowed (same fetched_at
        # can produce same price entry, which is harmless for queries).
        times = [t for t, _ in s]
        idx = bisect.bisect_left(times, product.fetched_at)
        s.insert(idx, (product.fetched_at, product.price_vnd))

    def history(
        self,
        item_id: int,
        shop_id: int,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[tuple[datetime, int]]:
        s = self._series.get((item_id, shop_id), [])
        if since is None and until is None:
            return list(s)
        lo = 0
        hi = len(s)
        if since is not None:
            lo = bisect.bisect_left([t for t, _ in s], since)
        if until is not None:
            hi = bisect.bisect_right([t for t, _ in s], until)
        return s[lo:hi]

    def min_max(self, item_id: int, shop_id: int) -> tuple[int, int] | None:
        s = self._series.get((item_id, shop_id))
        if not s:
            return None
        prices = [p for _, p in s]
        return min(prices), max(prices)


class Warehouse:
    """Composite of the three tables — what callers actually inject into."""

    def __init__(self) -> None:
        self.products = ProductFacts()
        self.shops = ShopFacts()
        self.price_history = PriceHistory()

    def ingest_product(self, product: ShopeeProduct) -> None:
        self.products.upsert(product)
        self.price_history.append(product)

    def ingest_products(self, products: Iterable[ShopeeProduct]) -> None:
        for p in products:
            self.ingest_product(p)

    def ingest_shop(self, shop: ShopeeShop) -> None:
        self.shops.upsert(shop)

    def ingest_shops(self, shops: Iterable[ShopeeShop]) -> None:
        for s in shops:
            self.ingest_shop(s)


__all__ = ["PriceHistory", "ProductFacts", "ShopFacts", "Warehouse"]
