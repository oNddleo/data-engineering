"""Type-checked JSONL codec for Customer / Order / RFMScore / CLVForecast."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from clvseg.clv import CLVForecast
from clvseg.schema import Customer, Order, RFMScore, Segment

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


def customer_to_dict(c: Customer) -> dict[str, object]:
    return {
        "customer_id": c.customer_id,
        "registered_at": c.registered_at.isoformat(),
        "city_key": c.city_key,
    }


def customer_from_dict(d: dict[str, object]) -> Customer:
    return Customer(
        customer_id=_require_str(d, "customer_id"),
        registered_at=datetime.fromisoformat(_require_str(d, "registered_at")),
        city_key=_require_str(d, "city_key"),
    )


def order_to_dict(o: Order) -> dict[str, object]:
    return {
        "order_id": o.order_id,
        "customer_id": o.customer_id,
        "gross_vnd": o.gross_vnd,
        "n_items": o.n_items,
        "placed_at": o.placed_at.isoformat(),
    }


def order_from_dict(d: dict[str, object]) -> Order:
    return Order(
        order_id=_require_str(d, "order_id"),
        customer_id=_require_str(d, "customer_id"),
        gross_vnd=_require_int(d, "gross_vnd"),
        n_items=_require_int(d, "n_items"),
        placed_at=datetime.fromisoformat(_require_str(d, "placed_at")),
    )


def score_to_dict(s: RFMScore) -> dict[str, object]:
    return {
        "customer_id": s.customer_id,
        "as_of": s.as_of.isoformat(),
        "recency_days": s.recency_days,
        "frequency": s.frequency,
        "monetary_vnd": s.monetary_vnd,
        "r_score": s.r_score,
        "f_score": s.f_score,
        "m_score": s.m_score,
    }


def score_from_dict(d: dict[str, object]) -> RFMScore:
    return RFMScore(
        customer_id=_require_str(d, "customer_id"),
        as_of=datetime.fromisoformat(_require_str(d, "as_of")),
        recency_days=_require_int(d, "recency_days"),
        frequency=_require_int(d, "frequency"),
        monetary_vnd=_require_int(d, "monetary_vnd"),
        r_score=_require_int(d, "r_score"),
        f_score=_require_int(d, "f_score"),
        m_score=_require_int(d, "m_score"),
    )


def clv_to_dict(f: CLVForecast) -> dict[str, object]:
    return {
        "customer_id": f.customer_id,
        "segment": f.segment.value,
        "historical_aov_vnd": f.historical_aov_vnd,
        "historical_frequency": f.historical_frequency,
        "window_days": f.window_days,
        "expected_lifetime_days": f.expected_lifetime_days,
        "forecast_vnd": f.forecast_vnd,
    }


def clv_from_dict(d: dict[str, object]) -> CLVForecast:
    return CLVForecast(
        customer_id=_require_str(d, "customer_id"),
        segment=Segment(_require_str(d, "segment")),
        historical_aov_vnd=_require_int(d, "historical_aov_vnd"),
        historical_frequency=_require_int(d, "historical_frequency"),
        window_days=_require_int(d, "window_days"),
        expected_lifetime_days=_require_int(d, "expected_lifetime_days"),
        forecast_vnd=_require_int(d, "forecast_vnd"),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_customers(customers: Iterable[Customer]) -> str:
    return _dump(customer_to_dict(c) for c in customers)


def dump_orders(orders: Iterable[Order]) -> str:
    return _dump(order_to_dict(o) for o in orders)


def dump_scores(scores: Iterable[RFMScore]) -> str:
    return _dump(score_to_dict(s) for s in scores)


def dump_clvs(forecasts: Iterable[CLVForecast]) -> str:
    return _dump(clv_to_dict(f) for f in forecasts)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_customers(text: str) -> Iterator[Customer]:
    for d in _iter_lines(text):
        yield customer_from_dict(d)


def load_orders(text: str) -> Iterator[Order]:
    for d in _iter_lines(text):
        yield order_from_dict(d)


def load_scores(text: str) -> Iterator[RFMScore]:
    for d in _iter_lines(text):
        yield score_from_dict(d)


def load_clvs(text: str) -> Iterator[CLVForecast]:
    for d in _iter_lines(text):
        yield clv_from_dict(d)


__all__ = [
    "clv_from_dict",
    "clv_to_dict",
    "customer_from_dict",
    "customer_to_dict",
    "dump_clvs",
    "dump_customers",
    "dump_orders",
    "dump_scores",
    "load_clvs",
    "load_customers",
    "load_orders",
    "load_scores",
    "order_from_dict",
    "order_to_dict",
    "score_from_dict",
    "score_to_dict",
]
