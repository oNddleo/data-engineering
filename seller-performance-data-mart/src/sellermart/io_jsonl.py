"""Type-checked JSONL codec for sources + facts."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from sellermart.schema import FactSellerDay
from sellermart.sources import Order, Return, Review

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


def order_to_dict(o: Order) -> dict[str, object]:
    return {
        "order_id": o.order_id,
        "seller_id": o.seller_id,
        "buyer_id": o.buyer_id,
        "category_key": o.category_key,
        "n_units": o.n_units,
        "gross_vnd": o.gross_vnd,
        "created_at": o.created_at.isoformat(),
    }


def order_from_dict(d: dict[str, object]) -> Order:
    return Order(
        order_id=_require_str(d, "order_id"),
        seller_id=_require_int(d, "seller_id"),
        buyer_id=_require_str(d, "buyer_id"),
        category_key=_require_str(d, "category_key"),
        n_units=_require_int(d, "n_units"),
        gross_vnd=_require_int(d, "gross_vnd"),
        created_at=datetime.fromisoformat(_require_str(d, "created_at")),
    )


def return_to_dict(r: Return) -> dict[str, object]:
    return {
        "return_id": r.return_id,
        "order_id": r.order_id,
        "seller_id": r.seller_id,
        "refund_vnd": r.refund_vnd,
        "created_at": r.created_at.isoformat(),
    }


def return_from_dict(d: dict[str, object]) -> Return:
    return Return(
        return_id=_require_str(d, "return_id"),
        order_id=_require_str(d, "order_id"),
        seller_id=_require_int(d, "seller_id"),
        refund_vnd=_require_int(d, "refund_vnd"),
        created_at=datetime.fromisoformat(_require_str(d, "created_at")),
    )


def review_to_dict(r: Review) -> dict[str, object]:
    return {
        "review_id": r.review_id,
        "order_id": r.order_id,
        "seller_id": r.seller_id,
        "rating_x100": r.rating_x100,
        "created_at": r.created_at.isoformat(),
    }


def review_from_dict(d: dict[str, object]) -> Review:
    return Review(
        review_id=_require_str(d, "review_id"),
        order_id=_require_str(d, "order_id"),
        seller_id=_require_int(d, "seller_id"),
        rating_x100=_require_int(d, "rating_x100"),
        created_at=datetime.fromisoformat(_require_str(d, "created_at")),
    )


def fact_to_dict(f: FactSellerDay) -> dict[str, object]:
    return {
        "seller_id": f.seller_id,
        "date_key": f.date_key,
        "n_orders": f.n_orders,
        "n_units": f.n_units,
        "gmv_vnd": f.gmv_vnd,
        "n_returns": f.n_returns,
        "refund_vnd": f.refund_vnd,
        "n_reviews": f.n_reviews,
        "sum_rating_x100": f.sum_rating_x100,
        "n_unique_buyers": f.n_unique_buyers,
    }


def fact_from_dict(d: dict[str, object]) -> FactSellerDay:
    return FactSellerDay(
        seller_id=_require_int(d, "seller_id"),
        date_key=_require_int(d, "date_key"),
        n_orders=_require_int(d, "n_orders"),
        n_units=_require_int(d, "n_units"),
        gmv_vnd=_require_int(d, "gmv_vnd"),
        n_returns=_require_int(d, "n_returns"),
        refund_vnd=_require_int(d, "refund_vnd"),
        n_reviews=_require_int(d, "n_reviews"),
        sum_rating_x100=_require_int(d, "sum_rating_x100"),
        n_unique_buyers=_require_int(d, "n_unique_buyers"),
    )


def _dump_lines(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_orders(orders: Iterable[Order]) -> str:
    return _dump_lines(order_to_dict(o) for o in orders)


def dump_returns(returns: Iterable[Return]) -> str:
    return _dump_lines(return_to_dict(r) for r in returns)


def dump_reviews(reviews: Iterable[Review]) -> str:
    return _dump_lines(review_to_dict(r) for r in reviews)


def dump_facts(facts: Iterable[FactSellerDay]) -> str:
    return _dump_lines(fact_to_dict(f) for f in facts)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_orders(text: str) -> Iterator[Order]:
    for d in _iter_lines(text):
        yield order_from_dict(d)


def load_returns(text: str) -> Iterator[Return]:
    for d in _iter_lines(text):
        yield return_from_dict(d)


def load_reviews(text: str) -> Iterator[Review]:
    for d in _iter_lines(text):
        yield review_from_dict(d)


def load_facts(text: str) -> Iterator[FactSellerDay]:
    for d in _iter_lines(text):
        yield fact_from_dict(d)


__all__ = [
    "dump_facts",
    "dump_orders",
    "dump_returns",
    "dump_reviews",
    "fact_from_dict",
    "fact_to_dict",
    "load_facts",
    "load_orders",
    "load_returns",
    "load_reviews",
    "order_from_dict",
    "order_to_dict",
    "return_from_dict",
    "return_to_dict",
    "review_from_dict",
    "review_to_dict",
]
