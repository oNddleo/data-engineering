"""Group events by buyer with an idle-gap session boundary.

The sessionizer is **per-buyer single-pass**:

1. Sort events for the buyer by ``occurred_at``.
2. Open a new session on the first event.
3. Keep appending to the current session as long as the gap to the
   next event is ≤ ``idle_gap_minutes``.
4. ``COMPLETE_CHECKOUT`` and ``ABANDON_CHECKOUT`` immediately close
   the current session — the next event opens a new one even if it
   arrives within the idle gap. This matches industry convention:
   after a successful checkout the buyer's *next* product view is
   a new shopping intent, not a continuation.
5. Cart value is tracked as a running sum: ``ADD_TO_CART`` adds
   ``unit_price_vnd``, ``REMOVE_FROM_CART`` subtracts. The session's
   ``cart_value_vnd`` is **clamped at zero** — a remove without a
   matching add (out-of-order webhook) shouldn't produce a negative
   cart.

Industry-standard ``idle_gap_minutes`` is 30 minutes; we expose it
as a parameter so AB testing different windows is straightforward.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from cartrec.schema import EventKind, Session

if TYPE_CHECKING:
    from collections.abc import Iterable

    from cartrec.schema import Event


def _close_session(
    buyer_id: str,
    bucket: list[Event],
    cart_value: int,
    distinct_items: set[str],
    explicit_abandon: bool,
) -> Session:
    n_views = sum(1 for e in bucket if e.kind is EventKind.VIEW_ITEM)
    n_add = sum(1 for e in bucket if e.kind is EventKind.ADD_TO_CART)
    n_remove = sum(1 for e in bucket if e.kind is EventKind.REMOVE_FROM_CART)
    started = any(e.kind is EventKind.START_CHECKOUT for e in bucket)
    completed = any(e.kind is EventKind.COMPLETE_CHECKOUT for e in bucket)
    return Session(
        session_id=f"{buyer_id}|{bucket[0].occurred_at.isoformat()}",
        buyer_id=buyer_id,
        started_at=bucket[0].occurred_at,
        ended_at=bucket[-1].occurred_at,
        n_events=len(bucket),
        n_views=n_views,
        n_add=n_add,
        n_remove=n_remove,
        cart_value_vnd=max(0, cart_value),
        distinct_items=len(distinct_items),
        started_checkout=started,
        completed_checkout=completed,
        explicit_abandon=explicit_abandon,
    )


def sessionize(
    events: Iterable[Event],
    *,
    idle_gap_minutes: int = 30,
) -> list[Session]:
    """Fold events into sessions per buyer.

    Output is sorted by ``(buyer_id, started_at)`` for stable diffs.
    """
    if idle_gap_minutes <= 0:
        raise ValueError("idle_gap_minutes must be > 0")
    by_buyer: dict[str, list[Event]] = defaultdict(list)
    for ev in events:
        by_buyer[ev.buyer_id].append(ev)

    out: list[Session] = []
    for buyer_id, group in by_buyer.items():
        group.sort(key=lambda e: e.occurred_at)
        bucket: list[Event] = []
        cart_value = 0
        distinct_items: set[str] = set()
        explicit_abandon = False
        idle_threshold_seconds = idle_gap_minutes * 60
        for ev in group:
            if bucket:
                gap = (ev.occurred_at - bucket[-1].occurred_at).total_seconds()
                if gap > idle_threshold_seconds:
                    out.append(
                        _close_session(
                            buyer_id, bucket, cart_value, distinct_items, explicit_abandon
                        )
                    )
                    bucket = []
                    cart_value = 0
                    distinct_items = set()
                    explicit_abandon = False
            bucket.append(ev)
            if ev.kind is EventKind.ADD_TO_CART:
                cart_value += ev.unit_price_vnd or 0
                if ev.item_id:
                    distinct_items.add(ev.item_id)
            elif ev.kind is EventKind.REMOVE_FROM_CART:
                cart_value -= ev.unit_price_vnd or 0
                if ev.item_id:
                    distinct_items.discard(ev.item_id)
            elif ev.kind is EventKind.ABANDON_CHECKOUT:
                explicit_abandon = True
            # Force a session boundary right after a checkout-terminal event.
            if ev.kind in (EventKind.COMPLETE_CHECKOUT, EventKind.ABANDON_CHECKOUT):
                out.append(
                    _close_session(buyer_id, bucket, cart_value, distinct_items, explicit_abandon)
                )
                bucket = []
                cart_value = 0
                distinct_items = set()
                explicit_abandon = False
        if bucket:
            out.append(
                _close_session(buyer_id, bucket, cart_value, distinct_items, explicit_abandon)
            )

    out.sort(key=lambda s: (s.buyer_id, s.started_at))
    return out


__all__ = ["sessionize"]
