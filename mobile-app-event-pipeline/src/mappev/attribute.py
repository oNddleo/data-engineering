"""Last-touch attribution with Adjust/Appsflyer-style attribution windows.

Standard windows:

* **Click attribution** — 7 days. A click within 7 days before the
  install is creditable.
* **View-through attribution** — 24 hours (view-through is much
  weaker signal than click).

Matching order — the canonical Appsflyer order:

1. **Last qualifying click** within click-window of install.
2. **Last qualifying impression** within view-window of install
   (if no click matched).
3. **Organic** — no attributable touchpoint.

When multiple clicks tie on timestamp we pick the lexicographically
smaller ``event_id`` for determinism. View-through never overrides
a click match.

The function operates on the **full event stream** — caller doesn't
pre-split. We index clicks + impressions per ``device_id`` and walk
each INSTALL against the index.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import TYPE_CHECKING

from mappev.schema import Attribution, EventKind

if TYPE_CHECKING:
    from datetime import datetime

    from mappev.schema import Event


_DEFAULT_CLICK_WINDOW = timedelta(days=7)
_DEFAULT_VIEW_WINDOW = timedelta(hours=24)


def attribute(
    events: list[Event],
    *,
    click_window: timedelta = _DEFAULT_CLICK_WINDOW,
    view_window: timedelta = _DEFAULT_VIEW_WINDOW,
) -> list[Attribution]:
    """Build one ``Attribution`` per INSTALL event in ``events``.

    Output is sorted by ``(install_at, device_id)`` for stable diffs.
    """
    if click_window <= timedelta(0):
        raise ValueError("click_window must be positive")
    if view_window <= timedelta(0):
        raise ValueError("view_window must be positive")

    clicks_by_device: dict[str, list[Event]] = defaultdict(list)
    impressions_by_device: dict[str, list[Event]] = defaultdict(list)
    installs: list[Event] = []
    for e in events:
        if e.kind is EventKind.CLICK:
            clicks_by_device[e.device_id].append(e)
        elif e.kind is EventKind.IMPRESSION:
            impressions_by_device[e.device_id].append(e)
        elif e.kind is EventKind.INSTALL:
            installs.append(e)

    out: list[Attribution] = []
    for install in installs:
        # 1. Last qualifying click within the window.
        click_match = _pick_last(
            clicks_by_device.get(install.device_id, []),
            install.occurred_at,
            click_window,
        )
        if click_match is not None:
            lag = int((install.occurred_at - click_match.occurred_at).total_seconds())
            out.append(
                Attribution(
                    device_id=install.device_id,
                    install_at=install.occurred_at,
                    attributed_source=click_match.source,
                    attributed_campaign=click_match.campaign,
                    attribution_event_id=click_match.event_id,
                    attribution_lag_seconds=lag,
                )
            )
            continue
        # 2. Last qualifying impression within the view-through window.
        view_match = _pick_last(
            impressions_by_device.get(install.device_id, []),
            install.occurred_at,
            view_window,
        )
        if view_match is not None:
            lag = int((install.occurred_at - view_match.occurred_at).total_seconds())
            out.append(
                Attribution(
                    device_id=install.device_id,
                    install_at=install.occurred_at,
                    attributed_source=view_match.source,
                    attributed_campaign=view_match.campaign,
                    attribution_event_id=view_match.event_id,
                    attribution_lag_seconds=lag,
                )
            )
            continue
        # 3. Organic.
        out.append(
            Attribution(
                device_id=install.device_id,
                install_at=install.occurred_at,
                attributed_source="organic",
                attributed_campaign="",
                attribution_event_id=None,
                attribution_lag_seconds=0,
            )
        )

    out.sort(key=lambda a: (a.install_at, a.device_id))
    return out


def _pick_last(
    candidates: list[Event],
    pivot_at: datetime,
    window: timedelta,
) -> Event | None:
    """Pick the latest event in ``candidates`` that's within ``window``
    BEFORE ``pivot_at``. Ties broken by lexicographic ``event_id``.
    """
    qualifying = [
        e for e in candidates if e.occurred_at <= pivot_at and (pivot_at - e.occurred_at) <= window
    ]
    if not qualifying:
        return None
    qualifying.sort(key=lambda e: (e.occurred_at, e.event_id))
    return qualifying[-1]


__all__ = ["attribute"]
