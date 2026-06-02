"""Recovery campaign scheduler.

The bundled cadence is the **VN-marketplace standard** (Shopee CRM
plays, Lazada Retention Tools defaults):

| Delay (since session ended) | Channel | Rationale                     |
| --------------------------- | ------- | ----------------------------- |
| 1 hour                      | EMAIL   | Top-of-mind, cheap to send    |
| 24 hours                    | SMS     | Day-after follow-up, urgent   |
| 72 hours                    | PUSH    | Last-chance prompt            |

Each touch is scheduled at ``session.ended_at + delay``. The
scheduler does **not** actually send anything — it produces a list
of :class:`CampaignTouch` records that a production fulfilment
service (Shopee Notify, Lazada Push, Twilio, SendGrid) would consume.

Operators tune the cadence per-vertical via ``cadence=`` — the
default is exposed as :data:`DEFAULT_CADENCE` so callers can mix
custom delays / channels with the defaults.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from cartrec.schema import CampaignTouch, TouchChannel

if TYPE_CHECKING:
    from cartrec.detect import AbandonedSession


# (delay_minutes, channel) tuples.
DEFAULT_CADENCE: tuple[tuple[int, TouchChannel], ...] = (
    (60, TouchChannel.EMAIL),
    (24 * 60, TouchChannel.SMS),
    (72 * 60, TouchChannel.PUSH),
)


def schedule(
    abandoned: list[AbandonedSession],
    *,
    cadence: tuple[tuple[int, TouchChannel], ...] = DEFAULT_CADENCE,
    suppress_explicit_after: TouchChannel | None = None,
) -> list[CampaignTouch]:
    """Build the list of touches to fire for each abandoned session.

    ``suppress_explicit_after`` lets ops shorten the cadence for
    sessions that EXPLICITLY abandoned — a buyer who *closed* the
    checkout drawer is a higher-intent recovery target, but if they
    don't bite after the email it's often best not to bombard them
    with SMS + PUSH. Set this to e.g. ``TouchChannel.EMAIL`` to send
    only the first touch for explicit abandons.
    """
    if not cadence:
        raise ValueError("cadence must be non-empty")
    if any(d < 0 for d, _ in cadence):
        raise ValueError("cadence delays must be >= 0 minutes")
    out: list[CampaignTouch] = []
    touch_counter = 0
    for ab in abandoned:
        from cartrec.detect import AbandonReason

        for i, (delay_min, channel) in enumerate(cadence):
            if (
                suppress_explicit_after is not None
                and ab.reason is AbandonReason.EXPLICIT
                and i > 0
                and suppress_explicit_after is cadence[0][1]
            ):
                # Stop after the first touch for explicit abandons.
                break
            scheduled = ab.session.ended_at + timedelta(minutes=delay_min)
            out.append(
                CampaignTouch(
                    touch_id=f"T-{touch_counter:08d}",
                    session_id=ab.session.session_id,
                    buyer_id=ab.session.buyer_id,
                    channel=channel,
                    scheduled_at=scheduled,
                    delay_minutes=delay_min,
                )
            )
            touch_counter += 1
    return out


def filter_due(
    touches: list[CampaignTouch],
    now: object,
) -> list[CampaignTouch]:
    """Return the subset of touches whose ``scheduled_at`` ≤ ``now``.

    ``now`` is caller-supplied so tests pin time deterministically.
    """
    from datetime import datetime

    if not isinstance(now, datetime):
        raise TypeError(f"now must be a datetime, got {type(now).__name__}")
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return [t for t in touches if t.scheduled_at <= now]


__all__ = ["DEFAULT_CADENCE", "filter_due", "schedule"]
