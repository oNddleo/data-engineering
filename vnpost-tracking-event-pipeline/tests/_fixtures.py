"""Canonical builders for parcel events in tests."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from vnpost.schema import VN_TZ, CourierCode, ParcelEvent, ParcelEventKind

DEFAULT_TS = datetime(2026, 5, 18, 9, 0, 0, tzinfo=VN_TZ)


def make_event(**overrides: Any) -> ParcelEvent:
    defaults: dict[str, Any] = {
        "event_id": "E-0001",
        "tracking_id": "T-0001",
        "courier": CourierCode.GHN,
        "kind": ParcelEventKind.CREATED,
        "occurred_at": DEFAULT_TS,
        "hub_code": "",
        "note": "",
    }
    defaults.update(overrides)
    return ParcelEvent(**defaults)


def created(
    tracking: str, at: datetime, courier: CourierCode = CourierCode.GHN, event_id: str | None = None
) -> ParcelEvent:
    return make_event(
        event_id=event_id or f"C-{tracking}",
        tracking_id=tracking,
        courier=courier,
        kind=ParcelEventKind.CREATED,
        occurred_at=at,
    )


def picked_up(
    tracking: str,
    at: datetime,
    hub: str = "",
    courier: CourierCode = CourierCode.GHN,
    event_id: str | None = None,
) -> ParcelEvent:
    return make_event(
        event_id=event_id or f"P-{tracking}",
        tracking_id=tracking,
        courier=courier,
        kind=ParcelEventKind.PICKED_UP,
        occurred_at=at,
        hub_code=hub,
    )


def at_hub(
    tracking: str,
    at: datetime,
    hub: str,
    courier: CourierCode = CourierCode.GHN,
    event_id: str | None = None,
) -> ParcelEvent:
    return make_event(
        event_id=event_id or f"H-{tracking}-{hub}",
        tracking_id=tracking,
        courier=courier,
        kind=ParcelEventKind.AT_HUB,
        occurred_at=at,
        hub_code=hub,
    )


def in_transit(
    tracking: str,
    at: datetime,
    hub: str = "",
    courier: CourierCode = CourierCode.GHN,
    event_id: str | None = None,
) -> ParcelEvent:
    return make_event(
        event_id=event_id or f"T-{tracking}-{hub}",
        tracking_id=tracking,
        courier=courier,
        kind=ParcelEventKind.IN_TRANSIT,
        occurred_at=at,
        hub_code=hub,
    )


def out_for_delivery(
    tracking: str,
    at: datetime,
    hub: str,
    courier: CourierCode = CourierCode.GHN,
    event_id: str | None = None,
) -> ParcelEvent:
    return make_event(
        event_id=event_id or f"O-{tracking}",
        tracking_id=tracking,
        courier=courier,
        kind=ParcelEventKind.OUT_FOR_DELIVERY,
        occurred_at=at,
        hub_code=hub,
    )


def delivered(
    tracking: str, at: datetime, courier: CourierCode = CourierCode.GHN, event_id: str | None = None
) -> ParcelEvent:
    return make_event(
        event_id=event_id or f"D-{tracking}",
        tracking_id=tracking,
        courier=courier,
        kind=ParcelEventKind.DELIVERED,
        occurred_at=at,
    )


def return_to_sender(
    tracking: str, at: datetime, courier: CourierCode = CourierCode.GHN, event_id: str | None = None
) -> ParcelEvent:
    return make_event(
        event_id=event_id or f"R-{tracking}",
        tracking_id=tracking,
        courier=courier,
        kind=ParcelEventKind.RETURN_TO_SENDER,
        occurred_at=at,
    )


__all__ = [
    "DEFAULT_TS",
    "at_hub",
    "created",
    "delivered",
    "in_transit",
    "make_event",
    "out_for_delivery",
    "picked_up",
    "return_to_sender",
]
