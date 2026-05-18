"""Vietnamese public-holiday builder.

Builds the canonical 11-day public holiday list per Article 112 of
the **Bộ Luật Lao động 2019** (Labour Code), plus PM-announced
compensation days when a fixed holiday falls on a weekend.

Annual public holidays (Article 112):

| Holiday                              | Date                              |
| ------------------------------------ | --------------------------------- |
| Tết Dương Lịch (New Year)            | 1 January                         |
| Tết Nguyên Đán (Lunar New Year)      | 30/12 lunar (eve) + 4 days = 5 days |
| Giỗ Tổ Hùng Vương (Hung Kings)        | 10/3 lunar                        |
| Ngày Giải phóng miền Nam (Reunification) | 30 April                       |
| Ngày Quốc tế Lao động (Labour Day)    | 1 May                             |
| Quốc Khánh (National Day) + 1 day    | 2 September + 1 (Sep 1 or Sep 3)  |

Total: **11 paid public holidays per year**. Tết is the largest
block — typically 5 consecutive days from the eve (giao thừa,
30/12 lunar) through 4/1 lunar. The compensation rule: if a
fixed-date holiday falls on Sat/Sun, the next Mon/Tue is also
a day off.
"""

from __future__ import annotations

from datetime import date, timedelta

from vncal.lunar import gio_to_solar, max_year, min_year, tet_solar
from vncal.schema import Holiday, HolidayKind


def build_year(year: int) -> list[Holiday]:
    """Build the canonical 11-day public-holiday list for ``year``.

    Includes 5-day Tết block, Giỗ Tổ (lunar), 4 fixed solar
    holidays, and 1-day Quốc Khánh extension. Compensation days
    are appended at the end where applicable.

    Raises ``LookupError`` if Tết/Giỗ Tổ aren't bundled for ``year``.
    """
    if year < min_year() or year > max_year():
        raise LookupError(
            f"year {year} outside bundled range {min_year()}-{max_year()}",
        )

    out: list[Holiday] = []

    # 1. Tết Dương Lịch — 1 January (solar fixed)
    out.append(
        Holiday(
            date=date(year, 1, 1),
            name_vi="Tết Dương Lịch",
            name_en="New Year's Day",
            kind=HolidayKind.SOLAR_FIXED,
        )
    )

    # 2. Tết Nguyên Đán — 5 days starting from the eve
    tet = tet_solar(year)
    # Eve = giao thừa (30/12 lunar) = day before Mùng 1
    tet_block = [tet - timedelta(days=1)] + [tet + timedelta(days=i) for i in range(4)]
    tet_labels = (
        ("Tết Nguyên Đán (30 Tết)", "Lunar New Year's Eve"),
        ("Tết Nguyên Đán (Mùng 1)", "Lunar New Year — Day 1"),
        ("Tết Nguyên Đán (Mùng 2)", "Lunar New Year — Day 2"),
        ("Tết Nguyên Đán (Mùng 3)", "Lunar New Year — Day 3"),
        ("Tết Nguyên Đán (Mùng 4)", "Lunar New Year — Day 4"),
    )
    for d, (vi, en) in zip(tet_block, tet_labels, strict=True):
        out.append(Holiday(date=d, name_vi=vi, name_en=en, kind=HolidayKind.TET))

    # 3. Giỗ Tổ Hùng Vương — 10/3 lunar
    out.append(
        Holiday(
            date=gio_to_solar(year),
            name_vi="Giỗ Tổ Hùng Vương",
            name_en="Hung Kings Commemoration Day",
            kind=HolidayKind.LUNAR_FIXED,
        )
    )

    # 4. Ngày Giải phóng miền Nam — 30 April
    out.append(
        Holiday(
            date=date(year, 4, 30),
            name_vi="Ngày Giải phóng miền Nam",
            name_en="Reunification Day",
            kind=HolidayKind.SOLAR_FIXED,
        )
    )

    # 5. Ngày Quốc tế Lao động — 1 May
    out.append(
        Holiday(
            date=date(year, 5, 1),
            name_vi="Ngày Quốc tế Lao động",
            name_en="International Labour Day",
            kind=HolidayKind.SOLAR_FIXED,
        )
    )

    # 6. Quốc Khánh — 2 September + 1 extra day
    # Per 2019 Labour Code amendment: Sep 1 or Sep 3 (PM picks annually).
    # Default: Sep 1 (the day before), which is what most years use.
    out.append(
        Holiday(
            date=date(year, 9, 1),
            name_vi="Quốc Khánh (1/9)",
            name_en="National Day Eve",
            kind=HolidayKind.SOLAR_FIXED,
        )
    )
    out.append(
        Holiday(
            date=date(year, 9, 2),
            name_vi="Quốc Khánh",
            name_en="National Day",
            kind=HolidayKind.SOLAR_FIXED,
        )
    )

    # 7. Compensation days for fixed-date holidays falling on weekends.
    # Applies to both SOLAR_FIXED and LUNAR_FIXED; the 5-day TET block
    # is treated as one unit and not auto-compensated here.
    comp_kinds = (HolidayKind.SOLAR_FIXED, HolidayKind.LUNAR_FIXED)
    holiday_dates = {h.date for h in out}
    for h in list(out):
        if h.kind in comp_kinds and h.date.weekday() >= 5:
            # Saturday → next Monday; Sunday → next Monday.
            shift = 7 - h.date.weekday()
            comp = h.date + timedelta(days=shift)
            # Skip duplicates (multiple weekend holidays could collapse).
            while comp in holiday_dates:
                comp += timedelta(days=1)
            holiday_dates.add(comp)
            out.append(
                Holiday(
                    date=comp,
                    name_vi=f"Bù {h.name_vi}",
                    name_en=f"In lieu of {h.name_en}",
                    kind=HolidayKind.COMPENSATION,
                )
            )

    # Sort by date.
    out.sort(key=lambda h: h.date)
    return out


def build_years(start_year: int, end_year: int) -> list[Holiday]:
    """Build a holiday list across ``[start_year, end_year]`` inclusive."""
    if end_year < start_year:
        raise ValueError(f"end_year {end_year} before start_year {start_year}")
    out: list[Holiday] = []
    for y in range(start_year, end_year + 1):
        out.extend(build_year(y))
    return out


__all__ = ["build_year", "build_years"]
