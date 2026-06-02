"""Canonical event builders for tests."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from mappev.schema import VN_TZ, Event, EventKind

DEFAULT_TS = datetime(2026, 5, 17, 9, 0, 0, tzinfo=VN_TZ)


def make_event(**overrides: Any) -> Event:
    defaults: dict[str, Any] = {
        "event_id": "E-0001",
        "device_id": "D-0001",
        "kind": EventKind.INSTALL,
        "occurred_at": DEFAULT_TS,
        "source": "organic",
        "campaign": "",
        "revenue_vnd": 0,
        "in_app_event_name": "",
    }
    defaults.update(overrides)
    return Event(**defaults)


def click_event(
    device_id: str,
    at: datetime,
    source: str = "facebook",
    campaign: str = "vn_promo",
    event_id: str | None = None,
) -> Event:
    return make_event(
        event_id=event_id or f"C-{device_id}-{at.isoformat()}",
        device_id=device_id,
        kind=EventKind.CLICK,
        occurred_at=at,
        source=source,
        campaign=campaign,
    )


def impression_event(
    device_id: str,
    at: datetime,
    source: str = "facebook",
    campaign: str = "vn_promo",
    event_id: str | None = None,
) -> Event:
    return make_event(
        event_id=event_id or f"I-{device_id}-{at.isoformat()}",
        device_id=device_id,
        kind=EventKind.IMPRESSION,
        occurred_at=at,
        source=source,
        campaign=campaign,
    )


def install_event(device_id: str, at: datetime, event_id: str | None = None) -> Event:
    return make_event(
        event_id=event_id or f"INS-{device_id}",
        device_id=device_id,
        kind=EventKind.INSTALL,
        occurred_at=at,
        source="organic",
        campaign="",
    )


def open_event(device_id: str, at: datetime, event_id: str | None = None) -> Event:
    return make_event(
        event_id=event_id or f"O-{device_id}-{at.isoformat()}",
        device_id=device_id,
        kind=EventKind.OPEN,
        occurred_at=at,
        source="organic",
        campaign="",
    )


def purchase_event(
    device_id: str, at: datetime, amount_vnd: int, event_id: str | None = None
) -> Event:
    return make_event(
        event_id=event_id or f"P-{device_id}-{at.isoformat()}",
        device_id=device_id,
        kind=EventKind.PURCHASE,
        occurred_at=at,
        source="organic",
        campaign="",
        revenue_vnd=amount_vnd,
    )


__all__ = [
    "DEFAULT_TS",
    "click_event",
    "impression_event",
    "install_event",
    "make_event",
    "open_event",
    "purchase_event",
]
