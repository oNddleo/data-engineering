"""JSONL codec for ShopeeProduct + ShopeeShop."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from shopeedw.schema import ShopeeProduct, ShopeeShop

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def _require_bool(d: dict[str, object], key: str) -> bool:
    v = d[key]
    if not isinstance(v, bool):
        raise TypeError(f"{key} must be bool, got {type(v).__name__}")
    return v


def product_to_dict(p: ShopeeProduct) -> dict[str, object]:
    return {
        "item_id": p.item_id,
        "shop_id": p.shop_id,
        "name": p.name,
        "category_key": p.category_key,
        "price_vnd": p.price_vnd,
        "original_price_vnd": p.original_price_vnd,
        "stock": p.stock,
        "sold_count": p.sold_count,
        "rating_x100": p.rating_x100,
        "review_count": p.review_count,
        "fetched_at": p.fetched_at.isoformat(),
    }


def product_from_dict(d: dict[str, object]) -> ShopeeProduct:
    return ShopeeProduct(
        item_id=_require_int(d, "item_id"),
        shop_id=_require_int(d, "shop_id"),
        name=_require_str(d, "name"),
        category_key=_require_str(d, "category_key"),
        price_vnd=_require_int(d, "price_vnd"),
        original_price_vnd=_require_int(d, "original_price_vnd"),
        stock=_require_int(d, "stock"),
        sold_count=_require_int(d, "sold_count"),
        rating_x100=_require_int(d, "rating_x100"),
        review_count=_require_int(d, "review_count"),
        fetched_at=datetime.fromisoformat(_require_str(d, "fetched_at")),
    )


def shop_to_dict(s: ShopeeShop) -> dict[str, object]:
    return {
        "shop_id": s.shop_id,
        "name": s.name,
        "location_province_code": s.location_province_code,
        "rating_x100": s.rating_x100,
        "follower_count": s.follower_count,
        "response_rate_pct": s.response_rate_pct,
        "is_official": s.is_official,
        "fetched_at": s.fetched_at.isoformat(),
    }


def shop_from_dict(d: dict[str, object]) -> ShopeeShop:
    return ShopeeShop(
        shop_id=_require_int(d, "shop_id"),
        name=_require_str(d, "name"),
        location_province_code=_require_str(d, "location_province_code"),
        rating_x100=_require_int(d, "rating_x100"),
        follower_count=_require_int(d, "follower_count"),
        response_rate_pct=_require_int(d, "response_rate_pct"),
        is_official=_require_bool(d, "is_official"),
        fetched_at=datetime.fromisoformat(_require_str(d, "fetched_at")),
    )


def dump_products(ps: Iterable[ShopeeProduct]) -> str:
    return "\n".join(json.dumps(product_to_dict(p), ensure_ascii=False) for p in ps) + "\n"


def load_products(text: str) -> Iterator[ShopeeProduct]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield product_from_dict(json.loads(line))


def dump_shops(ss: Iterable[ShopeeShop]) -> str:
    return "\n".join(json.dumps(shop_to_dict(s), ensure_ascii=False) for s in ss) + "\n"


def load_shops(text: str) -> Iterator[ShopeeShop]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield shop_from_dict(json.loads(line))


__all__ = [
    "dump_products",
    "dump_shops",
    "load_products",
    "load_shops",
    "product_from_dict",
    "product_to_dict",
    "shop_from_dict",
    "shop_to_dict",
]
