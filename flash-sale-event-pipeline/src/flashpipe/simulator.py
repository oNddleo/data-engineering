"""Seeded synthetic flash-sale traffic generator.

We mimic the 11.11 / 12.12 traffic shape: most events are VIEWs on
a small "hot" subset of items, with an order conversion of roughly
1 %. Stampede + out-of-order noise are injection knobs.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from flashpipe.events import VN_TZ, Event, EventKind

_DEFAULT_BASE_TS = datetime(2026, 11, 11, 9, 0, 0, tzinfo=VN_TZ)


def _user_id(rng: random.Random) -> str:
    return f"U-{rng.randint(100_000, 999_999)}"


def _make_event(
    rng: random.Random,
    *,
    event_id: str,
    kind: EventKind,
    item_id: int,
    shop_id: int,
    created_at: datetime,
    user_id: str | None = None,
    quantity: int = 0,
    amount_vnd: int = 0,
) -> Event:
    return Event(
        event_id=event_id,
        kind=kind,
        user_id=user_id if user_id is not None else _user_id(rng),
        item_id=item_id,
        shop_id=shop_id,
        quantity=quantity,
        amount_vnd=amount_vnd,
        created_at=created_at,
    )


def generate(
    *,
    n_events: int = 1000,
    n_items: int = 20,
    seed: int = 0,
    base_time: datetime | None = None,
    inject_stampede_item: int | None = None,
    out_of_order_fraction: float = 0.0,
) -> list[Event]:
    """Build a deterministic flash-sale event stream.

    * ``n_events`` baseline events spread linearly over time.
    * ``inject_stampede_item`` — when set, that item gets a 100×
      view burst near the end of the stream.
    * ``out_of_order_fraction`` — fraction of events whose
      timestamps get shuffled backward by up to 2 seconds.
    """
    if not 0 <= out_of_order_fraction <= 1:
        raise ValueError("out_of_order_fraction must be in [0, 1]")
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS
    items = list(range(100_000, 100_000 + n_items))
    shops = list(range(1_000, 1_000 + max(1, n_items // 5)))
    serial = 0

    def next_id(prefix: str) -> str:
        nonlocal serial
        serial += 1
        return f"{prefix}-{serial:08d}"

    events: list[Event] = []
    for i in range(n_events):
        kind = rng.choices(
            (EventKind.VIEW, EventKind.ADD_TO_CART, EventKind.CHECKOUT, EventKind.ORDER),
            weights=(0.85, 0.10, 0.04, 0.01),
            k=1,
        )[0]
        item = rng.choice(items)
        shop = rng.choice(shops)
        ts = base + timedelta(milliseconds=i * 10)
        quantity = 0
        amount = 0
        if kind is EventKind.ORDER:
            quantity = rng.randint(1, 3)
            amount = quantity * rng.choice([99_000, 199_000, 499_000, 999_000])
        events.append(
            _make_event(
                rng,
                event_id=next_id("E"),
                kind=kind,
                item_id=item,
                shop_id=shop,
                created_at=ts,
                quantity=quantity,
                amount_vnd=amount,
            )
        )

    if inject_stampede_item is not None:
        anchor = base + timedelta(seconds=20)
        for j in range(200):
            events.append(
                _make_event(
                    rng,
                    event_id=next_id("STAMP"),
                    kind=EventKind.VIEW,
                    item_id=inject_stampede_item,
                    shop_id=1000,
                    created_at=anchor + timedelta(milliseconds=j * 5),
                )
            )

    if out_of_order_fraction > 0:
        n_disorder = int(len(events) * out_of_order_fraction)
        for idx in rng.sample(range(len(events)), n_disorder):
            e = events[idx]
            skew = timedelta(seconds=rng.uniform(0.1, 2.0))
            events[idx] = Event(
                event_id=e.event_id,
                kind=e.kind,
                user_id=e.user_id,
                item_id=e.item_id,
                shop_id=e.shop_id,
                quantity=e.quantity,
                amount_vnd=e.amount_vnd,
                created_at=e.created_at - skew,
            )

    # In a real Kafka topic, events arrive in producer order, not
    # event-time order. We return in production order — caller can
    # sort by created_at if they want a sanitized stream.
    return events


__all__ = ["generate"]
