"""Seeded synthetic event stream.

Models five buyer archetypes producing a realistic funnel mix:

* ``window_shopper`` — browses but never adds to cart.
* ``cart_filler`` — adds items, never starts checkout.
* ``checkout_dropoff`` — starts checkout, abandons before completing.
* ``explicit_abandon`` — opens checkout drawer, closes it.
* ``converter`` — completes checkout.

The recovery-window simulation is what makes this interesting:
after the abandon, ``recovery_fraction`` of those buyers come back
and convert via a synthetic ``COMPLETE_CHECKOUT`` placed within the
attribution window — exercising the attribution path with real
positives.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from cartrec.schema import VN_TZ, Event, EventKind

_DEFAULT_BASE_TS = datetime(2026, 5, 1, 9, 0, 0, tzinfo=VN_TZ)

# Catalogue of mock VN-marketplace items (item_id, unit price VND).
_CATALOGUE: tuple[tuple[str, int], ...] = (
    ("ITEM-AOM-001", 49_000),
    ("ITEM-AOM-002", 99_000),
    ("ITEM-PHONE-AIRPOD", 299_000),
    ("ITEM-PHONE-CASE", 89_000),
    ("ITEM-BEAUTY-LIPSTICK", 199_000),
    ("ITEM-BEAUTY-MASK-10P", 159_000),
    ("ITEM-LAPTOP-STAND", 499_000),
    ("ITEM-LAPTOP-MOUSE", 249_000),
    ("ITEM-APPLIANCE-FAN", 1_990_000),
)


def _make_event(  # type: ignore[no-untyped-def]
    counter: int, buyer_id: str, kind: EventKind, ts, *, item=None
):
    item_id = item[0] if item else None
    unit_price = item[1] if item else None
    return Event(
        event_id=f"E-{counter:08d}",
        buyer_id=buyer_id,
        kind=kind,
        occurred_at=ts,
        item_id=item_id,
        unit_price_vnd=unit_price,
    )


def generate(
    *,
    n_buyers: int = 200,
    seed: int = 0,
    base_time: datetime | None = None,
    recovery_fraction: float = 0.10,
) -> list[Event]:
    """Generate a coherent funnel-event stream for ``n_buyers``."""
    if n_buyers < 1:
        raise ValueError("n_buyers must be >= 1")
    if not 0.0 <= recovery_fraction <= 1.0:
        raise ValueError("recovery_fraction must be in [0, 1]")
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS

    archetypes = (
        "window_shopper",
        "cart_filler",
        "checkout_dropoff",
        "explicit_abandon",
        "converter",
    )
    weights = (0.20, 0.15, 0.25, 0.15, 0.25)

    events: list[Event] = []
    counter = 0
    for i in range(n_buyers):
        buyer_id = f"B-{i:06d}"
        arche = rng.choices(archetypes, weights=weights, k=1)[0]
        # Each buyer's session starts at a different time.
        session_start = base + timedelta(minutes=i * 11)
        cursor = session_start
        n_views = rng.randint(1, 5)
        for _ in range(n_views):
            item = rng.choice(_CATALOGUE)
            events.append(_make_event(counter, buyer_id, EventKind.VIEW_ITEM, cursor, item=item))
            counter += 1
            cursor += timedelta(minutes=rng.randint(1, 5))
        if arche == "window_shopper":
            continue

        # All cart-filling archetypes add 1-3 items.
        added_items: list[tuple[str, int]] = []
        for _ in range(rng.randint(1, 3)):
            item = rng.choice(_CATALOGUE)
            events.append(_make_event(counter, buyer_id, EventKind.ADD_TO_CART, cursor, item=item))
            counter += 1
            added_items.append(item)
            cursor += timedelta(minutes=rng.randint(1, 4))
        # Occasional remove.
        if added_items and rng.random() < 0.20:
            item = rng.choice(added_items)
            events.append(
                _make_event(counter, buyer_id, EventKind.REMOVE_FROM_CART, cursor, item=item)
            )
            counter += 1
            cursor += timedelta(minutes=rng.randint(1, 3))

        if arche == "cart_filler":
            continue

        # Checkout-bound archetypes hit START_CHECKOUT.
        cursor += timedelta(minutes=rng.randint(1, 5))
        events.append(_make_event(counter, buyer_id, EventKind.START_CHECKOUT, cursor))
        counter += 1

        if arche == "converter":
            cursor += timedelta(minutes=rng.randint(1, 8))
            events.append(_make_event(counter, buyer_id, EventKind.COMPLETE_CHECKOUT, cursor))
            counter += 1
        elif arche == "explicit_abandon":
            cursor += timedelta(minutes=rng.randint(1, 8))
            events.append(_make_event(counter, buyer_id, EventKind.ABANDON_CHECKOUT, cursor))
            counter += 1
        # ``checkout_dropoff``: no terminal — session times out implicitly.

        # Recovery: a fraction of abandoners come back later and convert
        # within 24h of the session end (within the email-touch window).
        if arche in ("checkout_dropoff", "explicit_abandon") and rng.random() < recovery_fraction:
            recovery_ts = cursor + timedelta(
                minutes=rng.randint(120, 22 * 60),  # 2h-22h later
            )
            events.append(
                _make_event(
                    counter, buyer_id, EventKind.VIEW_ITEM, recovery_ts, item=rng.choice(_CATALOGUE)
                )
            )
            counter += 1
            events.append(
                _make_event(
                    counter,
                    buyer_id,
                    EventKind.COMPLETE_CHECKOUT,
                    recovery_ts + timedelta(minutes=2),
                )
            )
            counter += 1

    return events


__all__ = ["generate"]
