"""Did the buyer convert within the attribution window of a touch?

Given a list of ``CampaignTouch`` records and the buyer's
post-touch event stream, mark each touch as either:

* **CONVERTED** — buyer hit ``COMPLETE_CHECKOUT`` within
  ``attribution_window_hours`` of the touch's ``scheduled_at``.
* **NOT_CONVERTED** — no completion in the window.

When multiple touches feed the same conversion (the email + the SMS
both arrived before the purchase), only the **first** touch within
the window gets the credit by default — that's the
**first-touch attribution** convention. ``last_touch=True`` flips
to last-touch.

Production VN-marketplace teams typically use **last-touch** because
the closer-in-time touch is more credibly causal, but the function
exposes both so analysts can run the comparison.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import TYPE_CHECKING

from cartrec.schema import EventKind

if TYPE_CHECKING:
    from cartrec.schema import CampaignTouch, Event


class AttributionVerdict(str, Enum):
    CONVERTED = "CONVERTED"
    NOT_CONVERTED = "NOT_CONVERTED"


@dataclass(frozen=True, slots=True)
class AttributedTouch:
    """A touch + whether it gets credit for a downstream conversion."""

    touch: CampaignTouch
    verdict: AttributionVerdict
    conversion_event_id: str | None  # set on CONVERTED


def attribute(
    touches: list[CampaignTouch],
    events: list[Event],
    *,
    attribution_window_hours: int = 24,
    last_touch: bool = False,
) -> list[AttributedTouch]:
    """Mark each touch CONVERTED / NOT_CONVERTED.

    Order is preserved from the input ``touches`` list.
    """
    if attribution_window_hours <= 0:
        raise ValueError("attribution_window_hours must be > 0")
    window = timedelta(hours=attribution_window_hours)

    # Index conversions per buyer, sorted by time.
    completes_by_buyer: dict[str, list[Event]] = defaultdict(list)
    for ev in events:
        if ev.kind is EventKind.COMPLETE_CHECKOUT:
            completes_by_buyer[ev.buyer_id].append(ev)
    for events_group in completes_by_buyer.values():
        events_group.sort(key=lambda e: e.occurred_at)

    # Group touches per buyer, ordered chronologically.
    touches_by_buyer: dict[str, list[CampaignTouch]] = defaultdict(list)
    for t in touches:
        touches_by_buyer[t.buyer_id].append(t)
    for touches_group in touches_by_buyer.values():
        touches_group.sort(key=lambda t: t.scheduled_at)

    # Per buyer, walk conversions; attach each conversion to either the
    # first or last touch whose window contains it.
    credit: dict[str, str] = {}  # touch_id → conversion_event_id
    for buyer_id, b_touches in touches_by_buyer.items():
        completes = completes_by_buyer.get(buyer_id, [])
        for conv in completes:
            candidates = [
                t
                for t in b_touches
                if t.scheduled_at <= conv.occurred_at <= t.scheduled_at + window
            ]
            if not candidates:
                continue
            winner = candidates[-1] if last_touch else candidates[0]
            # Only one conversion per touch — don't double-credit.
            if winner.touch_id not in credit:
                credit[winner.touch_id] = conv.event_id

    out: list[AttributedTouch] = []
    for t in touches:
        if t.touch_id in credit:
            out.append(
                AttributedTouch(
                    touch=t,
                    verdict=AttributionVerdict.CONVERTED,
                    conversion_event_id=credit[t.touch_id],
                )
            )
        else:
            out.append(
                AttributedTouch(
                    touch=t,
                    verdict=AttributionVerdict.NOT_CONVERTED,
                    conversion_event_id=None,
                )
            )
    return out


def conversion_rate(attributed: list[AttributedTouch]) -> float:
    """Fraction of touches that converted (`[0, 1]`)."""
    if not attributed:
        return 0.0
    n_converted = sum(1 for a in attributed if a.verdict is AttributionVerdict.CONVERTED)
    return n_converted / len(attributed)


def conversion_by_channel(attributed: list[AttributedTouch]) -> dict[str, float]:
    """Per-channel conversion rate."""
    by_channel: dict[str, list[AttributedTouch]] = defaultdict(list)
    for a in attributed:
        by_channel[a.touch.channel.value].append(a)
    return {ch: conversion_rate(group) for ch, group in by_channel.items()}


__all__ = [
    "AttributedTouch",
    "AttributionVerdict",
    "attribute",
    "conversion_by_channel",
    "conversion_rate",
]
