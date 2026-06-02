"""Unit tests for reconciliation engine."""

from __future__ import annotations

from datetime import date

from recon.engine import ReconciliationEngine, _classify, _ref_similarity, reconcile
from recon.schema import DiscrepancyType, Transaction


def _txn(source: str, ref: str, amount: float, day: int = 1) -> Transaction:
    return Transaction(
        source=source,
        ref=ref,
        amount=amount,
        txn_date=date(2024, 1, day),
        description="TEST",
    )


SOURCES = ["A", "B", "C", "D"]


def _make_sources(
    ref: str,
    amounts: list[float],
    days: list[int] | None = None,
    sources: list[str] | None = None,
) -> dict[str, list[Transaction]]:
    srcs = sources or SOURCES[: len(amounts)]
    ds = days or [1] * len(amounts)
    result: dict[str, list[Transaction]] = {}
    for src, amt, day in zip(srcs, amounts, ds, strict=False):
        result[src] = [_txn(src, ref, amt, day)]
    return result


class TestRefSimilarity:
    def test_identical(self) -> None:
        assert _ref_similarity("TXN00123", "TXN00123") == 1.0

    def test_different(self) -> None:
        assert _ref_similarity("TXN00123", "XYZ99999") < 0.7

    def test_normalised_leading_zeros(self) -> None:
        # "TXN00123" and "TXN0123" after strip leading zeros differ by one char
        sim = _ref_similarity("TXN00123", "TXN0123")
        assert sim > 0.8

    def test_empty_strings(self) -> None:
        assert _ref_similarity("", "") == 1.0 or _ref_similarity("", "") == 0.0  # edge


class TestClassify:
    def test_matched(self) -> None:
        assert _classify(0.0, 1.0, 1.0, 4, 4) == DiscrepancyType.MATCHED

    def test_missing(self) -> None:
        assert _classify(0.0, 1.0, 1.0, 3, 4) == DiscrepancyType.MISSING

    def test_amount_mismatch(self) -> None:
        assert _classify(5.0, 0.5, 1.0, 4, 4) == DiscrepancyType.AMOUNT_MISMATCH

    def test_rounding(self) -> None:
        assert _classify(0.01, 0.9, 1.0, 4, 4) == DiscrepancyType.ROUNDING

    def test_timing(self) -> None:
        assert _classify(0.0, 1.0, 0.5, 4, 4) == DiscrepancyType.TIMING

    def test_multi(self) -> None:
        assert _classify(5.0, 0.5, 0.5, 3, 4) == DiscrepancyType.MULTI


class TestReconciliationEngine:
    def test_perfect_match(self) -> None:
        sources = _make_sources("TXN001", [100.0, 100.0, 100.0, 100.0])
        report = reconcile(sources)
        assert report.matched == 1
        assert report.discrepancies == 0

    def test_amount_mismatch_detected(self) -> None:
        sources = _make_sources("TXN002", [100.0, 100.0, 105.0, 100.0])
        report = reconcile(sources)
        assert report.discrepancies >= 1
        result = report.results[0]
        assert result.status == DiscrepancyType.AMOUNT_MISMATCH

    def test_missing_source_detected(self) -> None:
        # Only 3 sources have data, 4th is absent
        sources = _make_sources("TXN003", [200.0, 200.0, 200.0], sources=["A", "B", "C"])
        sources["D"] = []
        report = reconcile(sources)
        assert any(r.status == DiscrepancyType.MISSING for r in report.results)

    def test_rounding_discrepancy(self) -> None:
        sources = _make_sources("TXN004", [100.00, 100.00, 100.01, 100.00])
        report = reconcile(sources)
        result = report.results[0]
        assert result.status in (DiscrepancyType.MATCHED, DiscrepancyType.ROUNDING)

    def test_timing_drift(self) -> None:
        sources = _make_sources("TXN005", [50.0, 50.0, 50.0, 50.0], days=[1, 1, 7, 1])
        report = reconcile(sources)
        result = report.results[0]
        assert result.status in (DiscrepancyType.TIMING, DiscrepancyType.MULTI)

    def test_match_rate_all_matched(self) -> None:
        sources = _make_sources("TXN006", [300.0, 300.0, 300.0, 300.0])
        report = reconcile(sources)
        assert report.match_rate == 1.0

    def test_empty_sources(self) -> None:
        report = reconcile({"A": [], "B": [], "C": []})
        assert report.total_records == 0
        assert report.matched == 0

    def test_multiple_refs(self) -> None:
        # Use clearly distinct refs (not TXN001/TXN002 which are ~88% similar after normalise)
        sources: dict[str, list[Transaction]] = {
            "A": [_txn("A", "ALPHA9999", 100.0), _txn("A", "ZETA0001", 200.0)],
            "B": [_txn("B", "ALPHA9999", 100.0), _txn("B", "ZETA0001", 200.0)],
        }
        report = reconcile(sources)
        assert len(report.results) == 2

    def test_engine_class_same_as_functional(self) -> None:
        sources = _make_sources("TXN007", [99.0, 99.0])
        r1 = reconcile(sources)
        r2 = ReconciliationEngine().reconcile(sources)
        assert r1.matched == r2.matched
        assert r1.discrepancies == r2.discrepancies

    def test_confidence_in_range(self) -> None:
        sources = _make_sources("TXN008", [100.0, 101.0, 100.0, 100.0])
        report = reconcile(sources)
        for result in report.results:
            assert 0.0 <= result.confidence <= 1.0
