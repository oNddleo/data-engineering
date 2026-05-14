"""5-year retention policy per Decision 2345/QĐ-NHNN Điều 7.

Records younger than 5 years (calendar-time) are ``ACTIVE`` — they
must remain searchable in hot storage.

Records older than 5 years are ``ARCHIVE_ELIGIBLE`` — they may be
moved to cold / immutable storage but **must not be deleted** while
any open legal hold (regulator investigation, court order) covers
them. We expose ``legal_hold_until`` as an optional per-record
override that pushes the eligibility date out.

5-year math is calendar-based: today minus exactly 5 years, with
Feb 29 falling back to Feb 28 in non-leap target years.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sbv2345.ledger import SealedAuditRecord


RETENTION_YEARS = 5


class RetentionStatus(str, Enum):
    """Where a record sits in its lifecycle."""

    ACTIVE = "ACTIVE"
    ARCHIVE_ELIGIBLE = "ARCHIVE_ELIGIBLE"


def retention_cutoff(today: date) -> date:
    """First date that's still inside the 5-year window relative to ``today``.

    Records whose seal date is **strictly before** the cutoff are
    archive-eligible.
    """
    try:
        return date(today.year - RETENTION_YEARS, today.month, today.day)
    except ValueError:
        # Feb 29 → Feb 28 in a non-leap target year.
        return date(today.year - RETENTION_YEARS, today.month, 28)


def status(record: SealedAuditRecord, today: date) -> RetentionStatus:
    cutoff = retention_cutoff(today)
    seal_date = record.sealed_at.date()
    if seal_date < cutoff:
        return RetentionStatus.ARCHIVE_ELIGIBLE
    return RetentionStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class RetentionSummary:
    """How many records are at each lifecycle stage as of a given date."""

    today: date
    active: int
    archive_eligible: int

    @property
    def total(self) -> int:
        return self.active + self.archive_eligible


def summarise(records: Iterable[SealedAuditRecord], *, today: date) -> RetentionSummary:
    active = 0
    archive = 0
    for r in records:
        if status(r, today) is RetentionStatus.ACTIVE:
            active += 1
        else:
            archive += 1
    return RetentionSummary(today=today, active=active, archive_eligible=archive)


def archive_candidates(
    records: Iterable[SealedAuditRecord], *, today: date
) -> list[SealedAuditRecord]:
    return [r for r in records if status(r, today) is RetentionStatus.ARCHIVE_ELIGIBLE]


__all__ = [
    "RETENTION_YEARS",
    "RetentionStatus",
    "RetentionSummary",
    "archive_candidates",
    "retention_cutoff",
    "status",
    "summarise",
]
