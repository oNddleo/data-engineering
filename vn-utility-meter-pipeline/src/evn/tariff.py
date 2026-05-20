"""EVN tariff schedule — 6-tier household + flat category rates.

The retail-electricity tariff is set by the Bộ Công Thương and
updated by EVN decisions; significant adjustments since 2022:

| Decision         | Effective    | Highlights                                  |
| ---------------- | ------------ | ------------------------------------------- |
| 2941/QĐ-BCT      | 2023-05-04   | First post-2019 increase (+3%)              |
| 1416/QĐ-EVN      | 2023-11-09   | Bậc-thang up +4.5%, tiers 1806–3151         |
| 2699/QĐ-BCT      | 2024-10-11   | Most recent broad-based hike (+4.8%)        |

We bundle the **2024-10-11** schedule as the current/default. The
``tariff_for_date(d)`` helper picks the schedule effective on date
``d``.

Household 6-tier progressive ("bậc thang") schedule
(Decision 2699/QĐ-BCT, effective 2024-10-11):

| Tier | Range (kWh) | VND/kWh |
| ---- | ----------- | ------- |
| 1    | 0 – 50      | 1 893   |
| 2    | 51 – 100    | 1 956   |
| 3    | 101 – 200   | 2 271   |
| 4    | 201 – 300   | 2 860   |
| 5    | 301 – 400   | 3 197   |
| 6    | 401 +       | 3 302   |

Flat category rates (same decision):

| Category     | VND/kWh |
| ------------ | ------- |
| BUSINESS     | 2 752   |
| ADMIN_PUBLIC | 2 005   |
| PRODUCTION   | 2 159   |
| AGRICULTURE  | 1 644   |
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from evn.schema import CustomerCategory


@dataclass(frozen=True, slots=True)
class TariffTier:
    """One band in a progressive tariff."""

    upper_bound_kwh: int | None  # None → the open-ended top tier
    vnd_per_kwh: int

    def __post_init__(self) -> None:
        if self.upper_bound_kwh is not None and self.upper_bound_kwh <= 0:
            raise ValueError(
                f"upper_bound_kwh must be > 0 or None, got {self.upper_bound_kwh}",
            )
        if self.vnd_per_kwh < 0:
            raise ValueError(f"vnd_per_kwh must be >= 0, got {self.vnd_per_kwh}")


@dataclass(frozen=True, slots=True)
class HouseholdTariff:
    """A progressive 6-tier household tariff."""

    tiers: tuple[TariffTier, ...]

    def __post_init__(self) -> None:
        if not self.tiers:
            raise ValueError("tiers must be non-empty")
        # All but the last must have a finite upper bound.
        for i, tier in enumerate(self.tiers[:-1]):
            if tier.upper_bound_kwh is None:
                raise ValueError(
                    f"non-terminal tier {i} must have a finite upper_bound_kwh",
                )
        if self.tiers[-1].upper_bound_kwh is not None:
            raise ValueError(
                "the last tier must have upper_bound_kwh=None (open-ended)",
            )
        # Upper bounds must be strictly ascending.
        for i in range(1, len(self.tiers) - 1):
            prev_bound = self.tiers[i - 1].upper_bound_kwh
            this_bound = self.tiers[i].upper_bound_kwh
            assert prev_bound is not None and this_bound is not None
            if prev_bound >= this_bound:
                raise ValueError(
                    f"tier bounds not strictly ascending at index {i}",
                )


@dataclass(frozen=True, slots=True)
class FlatTariff:
    """Single VND/kWh rate, used for non-household categories."""

    vnd_per_kwh: int

    def __post_init__(self) -> None:
        if self.vnd_per_kwh < 0:
            raise ValueError(f"vnd_per_kwh must be >= 0, got {self.vnd_per_kwh}")


@dataclass(frozen=True, slots=True)
class TariffSchedule:
    """One historically-bounded tariff snapshot."""

    effective_from: date
    decision: str  # e.g. "2699/QĐ-BCT"
    household: HouseholdTariff
    business: FlatTariff
    admin_public: FlatTariff
    production: FlatTariff
    agriculture: FlatTariff

    def flat_for(self, category: CustomerCategory) -> FlatTariff:
        """Look up the flat-rate tariff for a non-household category."""
        if category is CustomerCategory.BUSINESS:
            return self.business
        if category is CustomerCategory.ADMIN_PUBLIC:
            return self.admin_public
        if category is CustomerCategory.PRODUCTION:
            return self.production
        if category is CustomerCategory.AGRICULTURE:
            return self.agriculture
        raise ValueError(
            f"category {category.value} has no flat tariff (use household)",
        )


# ---------- Bundled schedules ---------------------------------------------


# 2024-10-11 — most recent broad-based hike.
SCHEDULE_2024_10 = TariffSchedule(
    effective_from=date(2024, 10, 11),
    decision="2699/QĐ-BCT",
    household=HouseholdTariff(
        tiers=(
            TariffTier(upper_bound_kwh=50, vnd_per_kwh=1_893),
            TariffTier(upper_bound_kwh=100, vnd_per_kwh=1_956),
            TariffTier(upper_bound_kwh=200, vnd_per_kwh=2_271),
            TariffTier(upper_bound_kwh=300, vnd_per_kwh=2_860),
            TariffTier(upper_bound_kwh=400, vnd_per_kwh=3_197),
            TariffTier(upper_bound_kwh=None, vnd_per_kwh=3_302),
        )
    ),
    business=FlatTariff(vnd_per_kwh=2_752),
    admin_public=FlatTariff(vnd_per_kwh=2_005),
    production=FlatTariff(vnd_per_kwh=2_159),
    agriculture=FlatTariff(vnd_per_kwh=1_644),
)


# 2023-11-09 — prior schedule (1416/QĐ-EVN).
SCHEDULE_2023_11 = TariffSchedule(
    effective_from=date(2023, 11, 9),
    decision="1416/QĐ-EVN",
    household=HouseholdTariff(
        tiers=(
            TariffTier(upper_bound_kwh=50, vnd_per_kwh=1_806),
            TariffTier(upper_bound_kwh=100, vnd_per_kwh=1_866),
            TariffTier(upper_bound_kwh=200, vnd_per_kwh=2_167),
            TariffTier(upper_bound_kwh=300, vnd_per_kwh=2_729),
            TariffTier(upper_bound_kwh=400, vnd_per_kwh=3_050),
            TariffTier(upper_bound_kwh=None, vnd_per_kwh=3_151),
        )
    ),
    business=FlatTariff(vnd_per_kwh=2_628),
    admin_public=FlatTariff(vnd_per_kwh=1_914),
    production=FlatTariff(vnd_per_kwh=2_061),
    agriculture=FlatTariff(vnd_per_kwh=1_569),
)


_SCHEDULES: tuple[TariffSchedule, ...] = (
    SCHEDULE_2023_11,
    SCHEDULE_2024_10,
)


DEFAULT_SCHEDULE = SCHEDULE_2024_10


def tariff_for_date(d: date) -> TariffSchedule:
    """Return the tariff schedule in effect on date ``d``.

    Picks the latest schedule whose ``effective_from`` is on or
    before ``d``. Falls back to the earliest bundled schedule if
    ``d`` predates everything.
    """
    matching = [s for s in _SCHEDULES if s.effective_from <= d]
    if matching:
        return matching[-1]  # _SCHEDULES is sorted ascending
    return _SCHEDULES[0]


def all_schedules() -> tuple[TariffSchedule, ...]:
    return _SCHEDULES


__all__ = [
    "DEFAULT_SCHEDULE",
    "SCHEDULE_2023_11",
    "SCHEDULE_2024_10",
    "FlatTariff",
    "HouseholdTariff",
    "TariffSchedule",
    "TariffTier",
    "all_schedules",
    "tariff_for_date",
]
