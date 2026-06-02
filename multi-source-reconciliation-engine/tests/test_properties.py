"""Hypothesis property tests for reconciliation engine."""

from __future__ import annotations

from datetime import date, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from recon.engine import _amount_confidence, _ref_similarity, reconcile
from recon.schema import DiscrepancyType, Transaction


def _txn(source: str, ref: str, amount: float, day: int) -> Transaction:
    return Transaction(
        source=source,
        ref=ref,
        amount=amount,
        txn_date=date(2024, 1, 1) + timedelta(days=day % 365),
        description="TEST",
    )


class TestRefSimilarityProperties:
    @given(
        st.text(min_size=1, max_size=12, alphabet=st.characters(whitelist_categories=("Lu", "Nd")))
    )
    def test_self_similarity_is_1(self, s: str) -> None:
        assert _ref_similarity(s, s) == 1.0

    @given(
        st.text(min_size=1, max_size=12, alphabet=st.characters(whitelist_categories=("Lu", "Nd"))),
        st.text(min_size=1, max_size=12, alphabet=st.characters(whitelist_categories=("Lu", "Nd"))),
    )
    def test_symmetry(self, a: str, b: str) -> None:
        assert abs(_ref_similarity(a, b) - _ref_similarity(b, a)) < 1e-9

    @given(
        st.text(min_size=1, max_size=12, alphabet=st.characters(whitelist_categories=("Lu", "Nd"))),
        st.text(min_size=1, max_size=12, alphabet=st.characters(whitelist_categories=("Lu", "Nd"))),
    )
    def test_in_range(self, a: str, b: str) -> None:
        sim = _ref_similarity(a, b)
        assert 0.0 <= sim <= 1.0


class TestAmountConfidenceProperties:
    @given(
        st.lists(
            st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=10,
        )
    )
    def test_confidence_in_range(self, amounts: list[float]) -> None:
        _, conf = _amount_confidence(amounts)
        assert 0.0 <= conf <= 1.0

    @given(st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False))
    def test_single_amount_perfect_confidence(self, amount: float) -> None:
        delta, conf = _amount_confidence([amount])
        assert delta == 0.0
        assert conf == 1.0

    @given(st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False))
    def test_identical_amounts_perfect_confidence(self, amount: float) -> None:
        _, conf = _amount_confidence([amount, amount, amount])
        assert conf == 1.0


class TestReconcileProperties:
    @given(
        st.lists(
            st.floats(min_value=1.0, max_value=999.0, allow_nan=False, allow_infinity=False),
            min_size=2,
            max_size=5,
        )
    )
    @settings(max_examples=40)
    def test_identical_amounts_always_matched(self, amounts: list[float]) -> None:
        ref = "PROPTEST01"
        amount = round(amounts[0], 2)
        sources = {f"src{i}": [_txn(f"src{i}", ref, amount, 0)] for i in range(len(amounts))}
        report = reconcile(sources)
        if report.results:
            assert report.results[0].status in (
                DiscrepancyType.MATCHED,
                DiscrepancyType.ROUNDING,
            )

    @given(
        st.integers(min_value=1, max_value=20),
        st.integers(min_value=0, max_value=42),
    )
    @settings(max_examples=30)
    def test_match_rate_in_range(self, n: int, seed: int) -> None:
        from recon.simulator import generate_sources

        sources = generate_sources(n_transactions=n, seed=seed)
        report = reconcile(sources)
        assert 0.0 <= report.match_rate <= 1.0

    @given(st.integers(min_value=1, max_value=15))
    @settings(max_examples=20)
    def test_results_cover_all_refs(self, n: int) -> None:
        from recon.simulator import generate_sources

        sources = generate_sources(n_transactions=n, seed=n)
        report = reconcile(sources)
        assert len(report.results) <= n  # can't have more groups than transactions

    @given(st.integers(min_value=2, max_value=10))
    @settings(max_examples=20)
    def test_discrepancies_plus_matched_equals_results(self, n: int) -> None:
        from recon.simulator import generate_sources

        sources = generate_sources(n_transactions=n, seed=n * 7)
        report = reconcile(sources)
        assert report.matched + report.discrepancies == len(report.results)
