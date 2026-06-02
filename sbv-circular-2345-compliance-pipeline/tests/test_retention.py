"""5-year retention tests."""

from __future__ import annotations

from datetime import date, datetime

from sbv2345.ledger import AuditLedger
from sbv2345.retention import (
    RetentionStatus,
    archive_candidates,
    retention_cutoff,
    status,
    summarise,
)
from sbv2345.schema import VN_TZ

from ._fixtures import make_audit_event


def test_retention_cutoff_normal_date():
    assert retention_cutoff(date(2030, 6, 15)) == date(2025, 6, 15)


def test_retention_cutoff_handles_feb_29_to_non_leap():
    # 5 years before 2024-02-29 is 2019-02-29 — invalid; fall back to 28.
    assert retention_cutoff(date(2024, 2, 29)) == date(2019, 2, 28)


def test_status_active_just_inside_window():
    ledger = AuditLedger()
    sealed = datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ)
    rec = ledger.append(make_audit_event(), sealed_at=sealed)
    # Today exactly 5 years later = cutoff lands on same date → record
    # NOT strictly before cutoff → still ACTIVE.
    assert status(rec, date(2031, 5, 14)) is RetentionStatus.ACTIVE


def test_status_archive_one_day_past_window():
    ledger = AuditLedger()
    sealed = datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ)
    rec = ledger.append(make_audit_event(), sealed_at=sealed)
    # Cutoff for 2031-05-15 = 2026-05-15; rec sealed 2026-05-14 < cutoff.
    assert status(rec, date(2031, 5, 15)) is RetentionStatus.ARCHIVE_ELIGIBLE


def test_summarise_split_by_status():
    ledger = AuditLedger()
    old = datetime(2020, 5, 14, 9, 0, tzinfo=VN_TZ)
    new = datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ)
    for _ in range(3):
        ledger.append(make_audit_event(), sealed_at=old)
    for _ in range(2):
        ledger.append(make_audit_event(), sealed_at=new)
    s = summarise(ledger, today=date(2026, 6, 1))
    assert s.archive_eligible == 3
    assert s.active == 2
    assert s.total == 5


def test_archive_candidates_returns_old_only():
    ledger = AuditLedger()
    old = datetime(2018, 1, 1, 9, 0, tzinfo=VN_TZ)
    new = datetime(2026, 1, 1, 9, 0, tzinfo=VN_TZ)
    ledger.append(make_audit_event(), sealed_at=old)
    ledger.append(make_audit_event(), sealed_at=new)
    cands = archive_candidates(ledger, today=date(2026, 6, 1))
    assert len(cands) == 1
    assert cands[0].sealed_at == old


def test_retention_summary_total_property():
    from sbv2345.retention import RetentionSummary

    s = RetentionSummary(today=date(2026, 1, 1), active=10, archive_eligible=5)
    assert s.total == 15
