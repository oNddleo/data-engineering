"""Scraper Protocol + canned-response mock.

We deliberately don't ship an HTTP scraper for Shopee — that would
risk ToS issues + brittle network coupling in tests. Instead we
define a narrow Protocol so production deployments can plug in
their own scraper (using ``httpx``, ``aiohttp``, or whatever) and
the rest of this codebase (warehouse, aggregations) works against
any implementation.

:class:`MockShopeeScraper` returns whatever you register in its
constructor — for tests, that's predictable. Production swaps it
for a class with the same ``fetch_product`` / ``fetch_shop`` /
``list_products_by_category`` methods.

Note: respect Shopee's ``robots.txt`` and rate-limit headers in any
production scraper — this project doesn't bundle one because doing
it responsibly is a much larger undertaking than the data model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from shopeedw.schema import ShopeeProduct, ShopeeShop


class ShopeeScraper(Protocol):
    """The narrow contract a production scraper must satisfy."""

    def fetch_product(self, item_id: int, shop_id: int) -> ShopeeProduct | None: ...
    def fetch_shop(self, shop_id: int) -> ShopeeShop | None: ...
    def list_products_by_category(
        self, category_key: str, *, limit: int
    ) -> Iterator[ShopeeProduct]: ...


class ShopeeNotFoundError(LookupError):
    """Raised by callers when a scraper returns ``None`` for a lookup."""


class MockShopeeScraper:
    """Test-only scraper backed by in-memory dicts."""

    def __init__(
        self,
        products: Iterable[ShopeeProduct] = (),
        shops: Iterable[ShopeeShop] = (),
    ) -> None:
        self._products: dict[tuple[int, int], ShopeeProduct] = {}
        self._shops: dict[int, ShopeeShop] = {}
        for p in products:
            self._products[(p.item_id, p.shop_id)] = p
        for s in shops:
            self._shops[s.shop_id] = s

    def fetch_product(self, item_id: int, shop_id: int) -> ShopeeProduct | None:
        return self._products.get((item_id, shop_id))

    def fetch_shop(self, shop_id: int) -> ShopeeShop | None:
        return self._shops.get(shop_id)

    def list_products_by_category(
        self, category_key: str, *, limit: int
    ) -> Iterator[ShopeeProduct]:
        if limit <= 0:
            raise ValueError(f"limit must be > 0, got {limit}")
        out: list[ShopeeProduct] = []
        for p in self._products.values():
            if p.category_key == category_key:
                out.append(p)
                if len(out) >= limit:
                    break
        # Stable ordering for reproducibility — by gmv descending.
        out.sort(key=lambda p: (-p.gmv_vnd, p.item_id))
        return iter(out)

    def register_product(self, product: ShopeeProduct) -> None:
        self._products[(product.item_id, product.shop_id)] = product

    def register_shop(self, shop: ShopeeShop) -> None:
        self._shops[shop.shop_id] = shop

    @property
    def n_products(self) -> int:
        return len(self._products)

    @property
    def n_shops(self) -> int:
        return len(self._shops)


__all__ = ["MockShopeeScraper", "ShopeeNotFoundError", "ShopeeScraper"]
