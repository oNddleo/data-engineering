"""Mobile-app event schema.

Modelled on what Adjust / Appsflyer / AppMetrica emit and what VN
marketplaces (Shopee, Tiki, Lazada, MoMo, ZaloPay) ingest. The
event stream is the canonical input; attribution + cohort + LTV +
fraud detection all derive from it.

Six event kinds cover ~95% of mobile-app analytics:

| Kind          | Meaning                                                |
| ------------- | ------------------------------------------------------ |
| ``CLICK``     | Ad click on a promoted source/campaign.                |
| ``IMPRESSION``| Ad impression — used for view-through attribution.    |
| ``INSTALL``   | App opened for the first time on this device.          |
| ``OPEN``      | App opened on an already-installed device.             |
| ``IN_APP``    | Custom event (level_up, share, register, …).           |
| ``PURCHASE``  | Monetised in-app purchase.                             |

All money is integer VND. All timestamps are tz-aware.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class EventKind(str, Enum):
    """Six event kinds — the universe of mobile-app analytics."""

    CLICK = "CLICK"
    IMPRESSION = "IMPRESSION"
    INSTALL = "INSTALL"
    OPEN = "OPEN"
    IN_APP = "IN_APP"
    PURCHASE = "PURCHASE"


@dataclass(frozen=True, slots=True)
class Event:
    """One event line in the input stream.

    ``device_id`` is the cross-event join key (IDFA / GAID / AAID).
    ``source`` is the attribution source (e.g. ``"adjust"``,
    ``"appsflyer"``, ``"organic"``); ``campaign`` is the campaign
    name within that source.

    Money is integer VND; ``revenue_vnd=0`` for non-monetary events.
    """

    event_id: str
    device_id: str
    kind: EventKind
    occurred_at: datetime
    source: str  # "adjust", "appsflyer", "google_ads", "facebook", "organic"
    campaign: str  # campaign name; "" for organic
    revenue_vnd: int = 0
    in_app_event_name: str = ""  # only set when kind == IN_APP

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id must be non-empty")
        if not self.device_id:
            raise ValueError("device_id must be non-empty")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        if not self.source:
            raise ValueError("source must be non-empty (use 'organic' if direct)")
        if self.revenue_vnd < 0:
            raise ValueError(f"revenue_vnd must be >= 0, got {self.revenue_vnd}")
        if self.kind is EventKind.IN_APP and not self.in_app_event_name:
            raise ValueError("IN_APP events must have a non-empty in_app_event_name")
        if self.kind is not EventKind.IN_APP and self.in_app_event_name:
            raise ValueError(f"in_app_event_name must be empty for {self.kind.value} events")
        if self.kind is not EventKind.PURCHASE and self.revenue_vnd > 0:
            raise ValueError(
                f"revenue_vnd must be 0 for {self.kind.value} events, got {self.revenue_vnd}"
            )


@dataclass(frozen=True, slots=True)
class Attribution:
    """Result of attributing one install to a touchpoint."""

    device_id: str
    install_at: datetime
    attributed_source: str  # "organic" if no qualifying touchpoint
    attributed_campaign: str
    attribution_event_id: str | None  # the click/impression we attributed to; None for organic
    attribution_lag_seconds: int  # 0 for organic

    def __post_init__(self) -> None:
        if not self.device_id:
            raise ValueError("device_id must be non-empty")
        if self.install_at.tzinfo is None:
            raise ValueError("install_at must be timezone-aware")
        if not self.attributed_source:
            raise ValueError("attributed_source must be non-empty")
        if self.attribution_lag_seconds < 0:
            raise ValueError(
                f"attribution_lag_seconds must be >= 0, got {self.attribution_lag_seconds}"
            )


@dataclass(frozen=True, slots=True)
class CohortRetention:
    """Retention curve for one install cohort."""

    cohort_date: str  # ISO date of install day, e.g. "2026-05-14"
    cohort_size: int  # number of installs that day
    d1_active: int
    d7_active: int
    d30_active: int

    @property
    def d1_pct(self) -> float:
        return self.d1_active / self.cohort_size * 100 if self.cohort_size else 0.0

    @property
    def d7_pct(self) -> float:
        return self.d7_active / self.cohort_size * 100 if self.cohort_size else 0.0

    @property
    def d30_pct(self) -> float:
        return self.d30_active / self.cohort_size * 100 if self.cohort_size else 0.0


@dataclass(frozen=True, slots=True)
class CohortLTV:
    """Per-cohort LTV (revenue ÷ size) at various horizons."""

    cohort_date: str
    cohort_size: int
    revenue_d1_vnd: int
    revenue_d7_vnd: int
    revenue_d30_vnd: int

    @property
    def ltv_d1_vnd(self) -> int:
        return self.revenue_d1_vnd // self.cohort_size if self.cohort_size else 0

    @property
    def ltv_d7_vnd(self) -> int:
        return self.revenue_d7_vnd // self.cohort_size if self.cohort_size else 0

    @property
    def ltv_d30_vnd(self) -> int:
        return self.revenue_d30_vnd // self.cohort_size if self.cohort_size else 0


__all__ = [
    "VN_TZ",
    "Attribution",
    "CohortLTV",
    "CohortRetention",
    "Event",
    "EventKind",
]
