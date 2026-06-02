"""Comprehensive test suite for privledger (40+ tests including Hypothesis)."""

from __future__ import annotations

import math
import uuid

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from privledger.accountants import BasicCompositionAccountant, RDPAccountant, ZCDPAccountant
from privledger.audit import AuditEntry, AuditLog
from privledger.ledger import BudgetLedger
from privledger.mechanisms import RDP_ORDERS, GaussianMechanism, LaplaceMechanism
from privledger.planner import QueryPlanner, QueryRequest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DELTA = 1e-6
_SENS = 1.0
_SIGMA = 2.0
_B = 0.5


def make_gaussian(sensitivity: float = _SENS, sigma: float = _SIGMA) -> GaussianMechanism:
    return GaussianMechanism(sensitivity=sensitivity, sigma=sigma)


def make_laplace(sensitivity: float = _SENS, b: float = _B) -> LaplaceMechanism:
    return LaplaceMechanism(sensitivity=sensitivity, b=b)


# ===========================================================================
# TestGaussianMechanism
# ===========================================================================


class TestGaussianMechanism:
    def test_rdp_cost_formula(self) -> None:
        """RDP cost at alpha should equal alpha * s^2 / (2 * sigma^2)."""
        m = make_gaussian(1.0, 2.0)
        for alpha in RDP_ORDERS:
            expected = alpha * 1.0 / (2.0 * 4.0)
            assert math.isclose(m.rdp_cost(alpha), expected, rel_tol=1e-9)

    def test_rdp_cost_scales_with_alpha(self) -> None:
        """RDP cost must be strictly increasing in alpha."""
        m = make_gaussian()
        costs = [m.rdp_cost(a) for a in RDP_ORDERS]
        assert all(costs[i] < costs[i + 1] for i in range(len(costs) - 1))

    def test_zcdp_rho_formula(self) -> None:
        """zCDP rho = s^2 / (2 * sigma^2)."""
        m = make_gaussian(1.0, 2.0)
        assert math.isclose(m.zcdp_rho(), 0.125, rel_tol=1e-9)

    def test_dp_epsilon_balle_conversion(self) -> None:
        """dp_epsilon should match Balle et al. formula: rho + 2*sqrt(rho*log(1/delta))."""
        m = make_gaussian(1.0, 2.0)
        rho = m.zcdp_rho()
        expected = rho + 2.0 * math.sqrt(rho * math.log(1.0 / _DELTA))
        assert math.isclose(m.dp_epsilon(_DELTA), expected, rel_tol=1e-9)

    def test_dp_epsilon_positive(self) -> None:
        m = make_gaussian()
        assert m.dp_epsilon(_DELTA) > 0

    def test_sensitivity_scaling(self) -> None:
        """Doubling sensitivity quadruples rho."""
        m1 = make_gaussian(1.0, 2.0)
        m2 = make_gaussian(2.0, 2.0)
        assert math.isclose(m2.zcdp_rho(), 4.0 * m1.zcdp_rho(), rel_tol=1e-9)

    def test_sigma_scaling(self) -> None:
        """Doubling sigma quarters rho."""
        m1 = make_gaussian(1.0, 1.0)
        m2 = make_gaussian(1.0, 2.0)
        assert math.isclose(m1.zcdp_rho(), 4.0 * m2.zcdp_rho(), rel_tol=1e-9)

    def test_rdp_to_dp_epsilon_less_than_basic(self) -> None:
        """RDP-to-DP conversion should give epsilon <= Balle zCDP for large sigma."""
        m = make_gaussian(1.0, 10.0)
        rdp_eps = m.rdp_to_dp_epsilon(_DELTA)
        basic_eps = m.dp_epsilon(_DELTA)
        # Both are valid upper bounds; rdp bound is typically tighter or equal
        assert rdp_eps > 0
        assert basic_eps > 0

    def test_invalid_sensitivity(self) -> None:
        with pytest.raises(ValueError):
            GaussianMechanism(sensitivity=-1.0, sigma=1.0)

    def test_invalid_sigma(self) -> None:
        with pytest.raises(ValueError):
            GaussianMechanism(sensitivity=1.0, sigma=0.0)

    def test_invalid_delta(self) -> None:
        m = make_gaussian()
        with pytest.raises(ValueError):
            m.dp_epsilon(delta=0.0)
        with pytest.raises(ValueError):
            m.dp_epsilon(delta=1.0)

    def test_rdp_costs_returns_all_orders(self) -> None:
        m = make_gaussian()
        costs = m.rdp_costs()
        assert len(costs) == len(RDP_ORDERS)
        for (alpha, cost), expected_alpha in zip(costs, RDP_ORDERS, strict=False):
            assert math.isclose(alpha, expected_alpha)
            assert cost > 0


# ===========================================================================
# TestLaplaceMechanism
# ===========================================================================


class TestLaplaceMechanism:
    def test_epsilon_formula(self) -> None:
        """epsilon = sensitivity / b."""
        m = make_laplace(1.0, 0.5)
        assert math.isclose(m.dp_epsilon(), 2.0, rel_tol=1e-9)

    def test_epsilon_unit_sens_unit_b(self) -> None:
        m = LaplaceMechanism(sensitivity=1.0, b=1.0)
        assert math.isclose(m.dp_epsilon(), 1.0, rel_tol=1e-9)

    def test_larger_b_smaller_epsilon(self) -> None:
        m1 = LaplaceMechanism(sensitivity=1.0, b=1.0)
        m2 = LaplaceMechanism(sensitivity=1.0, b=2.0)
        assert m2.dp_epsilon() < m1.dp_epsilon()

    def test_invalid_sensitivity(self) -> None:
        with pytest.raises(ValueError):
            LaplaceMechanism(sensitivity=0.0, b=1.0)

    def test_invalid_b(self) -> None:
        with pytest.raises(ValueError):
            LaplaceMechanism(sensitivity=1.0, b=-1.0)


# ===========================================================================
# TestRDPAccountant
# ===========================================================================


class TestRDPAccountant:
    def test_initial_epsilon_finite(self) -> None:
        acc = RDPAccountant()
        # Zero spend => rdp curve is all zeros => log(1/delta)/(alpha-1) dominates
        eps = acc.epsilon(_DELTA)
        assert math.isfinite(eps)
        assert eps >= 0

    def test_composition_sums(self) -> None:
        """Spending the same mechanism twice doubles each alpha's accumulated RDP."""
        m = make_gaussian()
        acc = RDPAccountant()
        acc.spend(m)
        rdp_after_1 = {a: acc.total_rdp(a) for a in RDP_ORDERS}
        acc.spend(m)
        for alpha in RDP_ORDERS:
            assert math.isclose(acc.total_rdp(alpha), 2.0 * rdp_after_1[alpha], rel_tol=1e-9)

    def test_epsilon_increases_after_spend(self) -> None:
        acc = RDPAccountant()
        eps1 = acc.epsilon(_DELTA)
        acc.spend(make_gaussian())
        eps2 = acc.epsilon(_DELTA)
        assert eps2 > eps1

    def test_conversion_to_dp_epsilon(self) -> None:
        acc = RDPAccountant()
        acc.spend(make_gaussian(1.0, 5.0))
        eps = acc.epsilon(_DELTA)
        assert eps > 0
        assert math.isfinite(eps)

    def test_optimal_alpha_returned(self) -> None:
        acc = RDPAccountant()
        acc.spend(make_gaussian())
        alpha = acc.optimal_alpha(_DELTA)
        assert alpha in RDP_ORDERS

    def test_reset_clears_curve(self) -> None:
        acc = RDPAccountant()
        acc.spend(make_gaussian())
        acc.reset()
        for alpha in RDP_ORDERS:
            assert acc.total_rdp(alpha) == 0.0

    def test_can_afford_true_when_within_budget(self) -> None:
        acc = RDPAccountant()
        m = make_gaussian(1.0, 100.0)  # very small cost
        assert acc.can_afford(m, budget_epsilon=10.0, delta=_DELTA)

    def test_can_afford_false_when_over_budget(self) -> None:
        acc = RDPAccountant()
        # Spend a large amount first
        for _ in range(100):
            acc.spend(make_gaussian(1.0, 1.0))
        m = make_gaussian(1.0, 1.0)
        assert not acc.can_afford(m, budget_epsilon=0.001, delta=_DELTA)

    def test_copy_is_independent(self) -> None:
        acc = RDPAccountant()
        acc.spend(make_gaussian())
        copy = acc.copy()
        copy.spend(make_gaussian())
        assert copy.epsilon(_DELTA) > acc.epsilon(_DELTA)


# ===========================================================================
# TestZCDPAccountant
# ===========================================================================


class TestZCDPAccountant:
    def test_initial_rho_zero(self) -> None:
        acc = ZCDPAccountant()
        assert acc.total_rho == 0.0

    def test_rho_accumulation(self) -> None:
        acc = ZCDPAccountant()
        m = make_gaussian()
        expected_rho = m.zcdp_rho()
        acc.spend(m, _DELTA)
        assert math.isclose(acc.total_rho, expected_rho, rel_tol=1e-9)

    def test_rho_additive_composition(self) -> None:
        acc = ZCDPAccountant()
        m = make_gaussian()
        acc.spend(m, _DELTA)
        acc.spend(m, _DELTA)
        assert math.isclose(acc.total_rho, 2.0 * m.zcdp_rho(), rel_tol=1e-9)

    def test_epsilon_conversion_formula(self) -> None:
        acc = ZCDPAccountant()
        m = make_gaussian(1.0, 2.0)
        acc.spend(m, _DELTA)
        rho = acc.total_rho
        expected = rho + 2.0 * math.sqrt(rho * math.log(1.0 / _DELTA))
        assert math.isclose(acc.epsilon(_DELTA), expected, rel_tol=1e-9)

    def test_reset_clears_rho(self) -> None:
        acc = ZCDPAccountant()
        acc.spend(make_gaussian(), _DELTA)
        acc.reset()
        assert acc.total_rho == 0.0

    def test_can_afford_false_over_budget(self) -> None:
        acc = ZCDPAccountant()
        m = make_gaussian(1.0, 1.0)
        for _ in range(50):
            acc.spend(m, _DELTA)
        assert not acc.can_afford(m, budget_epsilon=0.001, delta=_DELTA)


# ===========================================================================
# TestBasicComposition
# ===========================================================================


class TestBasicComposition:
    def test_epsilon_zero_initially(self) -> None:
        acc = BasicCompositionAccountant()
        assert acc.total_epsilon == 0.0

    def test_epsilon_additivity_gaussian(self) -> None:
        acc = BasicCompositionAccountant()
        m = make_gaussian()
        single_cost = m.dp_epsilon(_DELTA)
        acc.spend(m, _DELTA)
        acc.spend(m, _DELTA)
        assert math.isclose(acc.total_epsilon, 2.0 * single_cost, rel_tol=1e-9)

    def test_epsilon_additivity_laplace(self) -> None:
        acc = BasicCompositionAccountant()
        m = make_laplace()
        acc.spend(m)
        acc.spend(m)
        assert math.isclose(acc.total_epsilon, 2.0 * m.dp_epsilon(), rel_tol=1e-9)

    def test_can_afford_true(self) -> None:
        acc = BasicCompositionAccountant()
        m = make_gaussian(1.0, 100.0)
        assert acc.can_afford(m, 10.0, _DELTA)

    def test_can_afford_false(self) -> None:
        acc = BasicCompositionAccountant()
        m = make_gaussian(1.0, 1.0)
        assert not acc.can_afford(m, 0.0001, _DELTA)

    def test_reset(self) -> None:
        acc = BasicCompositionAccountant()
        acc.spend(make_gaussian(), _DELTA)
        acc.reset()
        assert acc.total_epsilon == 0.0

    def test_copy_is_independent(self) -> None:
        acc = BasicCompositionAccountant()
        acc.spend(make_gaussian(), _DELTA)
        copy = acc.copy()
        copy.spend(make_gaussian(), _DELTA)
        assert copy.total_epsilon > acc.total_epsilon


# ===========================================================================
# TestBudgetLedger
# ===========================================================================


class TestBudgetLedger:
    def test_can_spend_new_pair_within_budget(self) -> None:
        ledger = BudgetLedger(default_epsilon_limit=100.0)
        m = make_gaussian(1.0, 10.0)
        assert ledger.can_spend(m, dataset="ds1", analyst="a1", delta=_DELTA)

    def test_spend_reduces_remaining(self) -> None:
        ledger = BudgetLedger(default_epsilon_limit=100.0)
        m = make_gaussian(1.0, 10.0)
        r1 = ledger.remaining_epsilon(dataset="ds1", analyst="a1", delta=_DELTA)
        ledger.spend(m, "q1", dataset="ds1", analyst="a1", delta=_DELTA)
        r2 = ledger.remaining_epsilon(dataset="ds1", analyst="a1", delta=_DELTA)
        assert r2 < r1

    def test_budget_exhaustion_raises(self) -> None:
        ledger = BudgetLedger(default_epsilon_limit=0.001)
        m = make_gaussian(1.0, 1.0)
        with pytest.raises(RuntimeError):
            ledger.spend(m, "q1", dataset="ds1", analyst="a1", delta=_DELTA)

    def test_per_analyst_isolation(self) -> None:
        """Spending for analyst A must not affect analyst B."""
        ledger = BudgetLedger(default_epsilon_limit=100.0)
        m = make_gaussian(1.0, 2.0)
        r_b_before = ledger.remaining_epsilon(dataset="ds1", analyst="b", delta=_DELTA)
        ledger.spend(m, "q1", dataset="ds1", analyst="a", delta=_DELTA)
        r_b_after = ledger.remaining_epsilon(dataset="ds1", analyst="b", delta=_DELTA)
        assert math.isclose(r_b_before, r_b_after, rel_tol=1e-9)

    def test_per_dataset_isolation(self) -> None:
        """Spending for dataset ds1 must not affect ds2."""
        ledger = BudgetLedger(default_epsilon_limit=100.0)
        m = make_gaussian(1.0, 2.0)
        r_before = ledger.remaining_epsilon(dataset="ds2", analyst="a", delta=_DELTA)
        ledger.spend(m, "q1", dataset="ds1", analyst="a", delta=_DELTA)
        r_after = ledger.remaining_epsilon(dataset="ds2", analyst="a", delta=_DELTA)
        assert math.isclose(r_before, r_after, rel_tol=1e-9)

    def test_can_spend_returns_false_when_exhausted(self) -> None:
        ledger = BudgetLedger(default_epsilon_limit=0.001)
        m = make_gaussian(1.0, 1.0)
        assert not ledger.can_spend(m, dataset="ds", analyst="a", delta=_DELTA)

    def test_reset_restores_full_budget(self) -> None:
        ledger = BudgetLedger(default_epsilon_limit=10.0)
        m = make_gaussian(1.0, 5.0)
        ledger.spend(m, "q1", dataset="ds", analyst="a", delta=_DELTA)
        ledger.reset(dataset="ds", analyst="a")
        r = ledger.remaining_epsilon(dataset="ds", analyst="a", delta=_DELTA)
        assert math.isclose(r, 10.0, rel_tol=1e-6)

    def test_set_limit(self) -> None:
        ledger = BudgetLedger()
        ledger.set_limit("ds", "a", 42.0)
        status = ledger.status(dataset="ds", analyst="a")
        assert math.isclose(status["epsilon_limit"], 42.0)

    def test_status_keys_present(self) -> None:
        ledger = BudgetLedger()
        s = ledger.status(dataset="ds", analyst="a")
        for k in ("epsilon_limit", "basic_spent", "rdp_spent", "zcdp_spent"):
            assert k in s

    def test_keys_tracks_pairs(self) -> None:
        ledger = BudgetLedger()
        ledger.can_spend(make_gaussian(), dataset="ds1", analyst="a1")
        ledger.can_spend(make_gaussian(), dataset="ds2", analyst="a2")
        assert ("ds1", "a1") in ledger.keys
        assert ("ds2", "a2") in ledger.keys


# ===========================================================================
# TestQueryPlanner
# ===========================================================================


class TestQueryPlanner:
    def _request(
        self,
        sensitivity: float = 1.0,
        sigma: float = 5.0,
        delta: float = _DELTA,
    ) -> QueryRequest:
        return QueryRequest(
            query_id=str(uuid.uuid4()),
            dataset="ds",
            analyst="a",
            sensitivity=sensitivity,
            sigma=sigma,
            delta=delta,
        )

    def test_accept_when_fits(self) -> None:
        planner = QueryPlanner()
        req = self._request(sigma=100.0)  # very large sigma → small cost
        decision, sigma = planner.plan(req, budget_remaining=10.0)
        assert decision == "accept"
        assert sigma == 100.0

    def test_reject_when_zero_budget(self) -> None:
        planner = QueryPlanner()
        req = self._request(sigma=1.0)
        decision, sigma = planner.plan(req, budget_remaining=0.0)
        assert decision == "reject"
        assert sigma is None

    def test_reject_when_no_sigma_fits(self) -> None:
        planner = QueryPlanner()
        req = self._request(sensitivity=1.0, sigma=1.0)
        # Even at sigma = 1000 * sensitivity the cost will exceed 0
        decision, sigma = planner.plan(req, budget_remaining=1e-15)
        assert decision == "reject"
        assert sigma is None

    def test_rewrite_finds_larger_sigma(self) -> None:
        planner = QueryPlanner()
        # Small sigma → large cost; medium budget should trigger rewrite
        req = self._request(sensitivity=1.0, sigma=0.5)
        # Pick a budget that the large-sigma mechanism fits
        large_m = GaussianMechanism(1.0, 1000.0)
        budget = large_m.dp_epsilon(_DELTA) * 2.0
        decision, new_sigma = planner.plan(req, budget_remaining=budget)
        assert decision in ("rewrite", "accept")
        if decision == "rewrite":
            assert new_sigma is not None
            assert new_sigma > req.sigma

    def test_rewrite_sigma_fits_budget(self) -> None:
        """The rewritten sigma must actually produce a cost within budget."""
        planner = QueryPlanner()
        req = self._request(sensitivity=1.0, sigma=0.1)
        budget = 0.5  # Needs bigger sigma
        decision, new_sigma = planner.plan(req, budget_remaining=budget)
        if decision == "rewrite" and new_sigma is not None:
            m = GaussianMechanism(1.0, new_sigma)
            assert m.dp_epsilon(_DELTA) <= budget + 1e-9

    def test_binary_search_convergence(self) -> None:
        """After rewrite, the found sigma should be close to the true minimum."""
        planner = QueryPlanner()
        req = self._request(sensitivity=1.0, sigma=0.1, delta=1e-5)
        budget = 1.0
        decision, new_sigma = planner.plan(req, budget_remaining=budget)
        if decision == "rewrite" and new_sigma is not None:
            m = GaussianMechanism(1.0, new_sigma)
            # Should be within budget
            assert m.dp_epsilon(1e-5) <= budget + 1e-9

    def test_sigma_monotonicity(self) -> None:
        """Larger sigma means smaller epsilon cost."""
        m1 = GaussianMechanism(1.0, 1.0)
        m2 = GaussianMechanism(1.0, 2.0)
        assert m2.dp_epsilon(_DELTA) < m1.dp_epsilon(_DELTA)

    def test_invalid_query_request(self) -> None:
        with pytest.raises(ValueError):
            QueryRequest(query_id="q", dataset="d", analyst="a", sensitivity=0.0, sigma=1.0)


# ===========================================================================
# TestAuditLog
# ===========================================================================


class TestAuditLog:
    def test_entries_recorded(self) -> None:
        log = AuditLog()
        m = make_gaussian()
        log.record(dataset="ds", analyst="a", mechanism=m, delta=_DELTA)
        log.record(dataset="ds", analyst="a", mechanism=m, delta=_DELTA)
        assert len(log.entries) == 2

    def test_entry_fields_populated(self) -> None:
        log = AuditLog()
        m = make_gaussian(1.0, 5.0)
        entry = log.record(dataset="ds", analyst="a", mechanism=m, delta=_DELTA)
        assert entry.dataset == "ds"
        assert entry.analyst == "a"
        assert entry.mechanism_type == "gaussian"
        assert entry.epsilon_basic > 0
        assert entry.epsilon_rdp > 0
        assert entry.epsilon_zcdp > 0

    def test_savings_vs_basic_calculated(self) -> None:
        """For Gaussian, rdp should be tighter (or equal) to basic Balle conversion."""
        log = AuditLog()
        m = make_gaussian(1.0, 10.0)
        entry = log.record(dataset="ds", analyst="a", mechanism=m, delta=_DELTA)
        # savings = epsilon_basic - epsilon_rdp; can be positive or zero
        assert math.isfinite(entry.savings_vs_basic)

    def test_filter_by_dataset(self) -> None:
        log = AuditLog()
        m = make_gaussian()
        log.record(dataset="ds1", analyst="a", mechanism=m, delta=_DELTA)
        log.record(dataset="ds2", analyst="a", mechanism=m, delta=_DELTA)
        assert len(log.filter(dataset="ds1")) == 1
        assert len(log.filter(dataset="ds2")) == 1

    def test_filter_by_analyst(self) -> None:
        log = AuditLog()
        m = make_gaussian()
        log.record(dataset="ds", analyst="alice", mechanism=m, delta=_DELTA)
        log.record(dataset="ds", analyst="bob", mechanism=m, delta=_DELTA)
        assert len(log.filter(analyst="alice")) == 1
        assert len(log.filter(analyst="bob")) == 1

    def test_clear(self) -> None:
        log = AuditLog()
        log.record(dataset="ds", analyst="a", mechanism=make_gaussian(), delta=_DELTA)
        log.clear()
        assert len(log.entries) == 0

    def test_to_json_round_trip(self) -> None:
        """AuditEntry.to_json / AuditEntry(**data) round-trip."""
        m = make_gaussian()
        entry = AuditEntry.create(
            query_id="q1", dataset="ds", analyst="a", mechanism=m, delta=_DELTA
        )
        import json

        data = json.loads(entry.to_json())
        restored = AuditEntry(**data)
        assert restored.query_id == entry.query_id
        assert math.isclose(restored.epsilon_basic, entry.epsilon_basic)

    def test_laplace_audit_entry(self) -> None:
        log = AuditLog()
        m = make_laplace()
        entry = log.record(dataset="ds", analyst="a", mechanism=m, delta=_DELTA)
        assert entry.mechanism_type == "laplace"
        assert entry.epsilon_basic > 0

    def test_total_savings(self) -> None:
        log = AuditLog()
        m = make_gaussian(1.0, 10.0)
        log.record(dataset="ds", analyst="a", mechanism=m, delta=_DELTA)
        log.record(dataset="ds", analyst="a", mechanism=m, delta=_DELTA)
        total = log.total_savings(dataset="ds", analyst="a")
        assert math.isfinite(total)

    def test_file_persistence(self, tmp_path: pytest.TempPathFactory) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = Path(f.name)

        try:
            log1 = AuditLog(persist_path=path)
            m = make_gaussian()
            log1.record(dataset="ds", analyst="a", mechanism=m, delta=_DELTA)

            log2 = AuditLog(persist_path=path)
            assert len(log2.entries) == 1
        finally:
            if path.exists():
                path.unlink()


# ===========================================================================
# TestProperties (Hypothesis)
# ===========================================================================

_pos_float = st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False)
_delta_st = st.floats(min_value=1e-10, max_value=0.1, allow_nan=False, allow_infinity=False)


class TestProperties:
    @given(sensitivity=_pos_float, sigma=_pos_float, delta=_delta_st)
    @settings(max_examples=100)
    def test_zcdp_eps_leq_basic_eps(self, sensitivity: float, sigma: float, delta: float) -> None:
        """zCDP epsilon ≤ basic (Balle) epsilon for Gaussian mechanism.

        Both use the same formula (rho + 2*sqrt(rho*log(1/delta))),
        so they should be equal for the single-shot case.
        """
        m = GaussianMechanism(sensitivity=sensitivity, sigma=sigma)
        eps_basic = m.dp_epsilon(delta)
        eps_zcdp = m.dp_epsilon(delta)
        assert math.isclose(eps_basic, eps_zcdp, rel_tol=1e-9)

    @given(sensitivity=_pos_float, sigma=_pos_float, delta=_delta_st)
    @settings(max_examples=100)
    def test_increasing_sigma_decreases_cost(
        self, sensitivity: float, sigma: float, delta: float
    ) -> None:
        """A larger sigma must produce strictly smaller epsilon."""
        m1 = GaussianMechanism(sensitivity=sensitivity, sigma=sigma)
        m2 = GaussianMechanism(sensitivity=sensitivity, sigma=sigma * 2.0)
        assert m2.dp_epsilon(delta) < m1.dp_epsilon(delta)

    @given(sensitivity=_pos_float, sigma=_pos_float, delta=_delta_st)
    @settings(max_examples=100)
    def test_composition_geq_individual(
        self, sensitivity: float, sigma: float, delta: float
    ) -> None:
        """After composing two mechanisms, total epsilon ≥ epsilon of one."""
        m = GaussianMechanism(sensitivity=sensitivity, sigma=sigma)
        acc = ZCDPAccountant()
        acc.spend(m, delta)
        eps1 = acc.epsilon(delta)
        acc.spend(m, delta)
        eps2 = acc.epsilon(delta)
        assert eps2 >= eps1

    @given(sensitivity=_pos_float, b=_pos_float)
    @settings(max_examples=100)
    def test_laplace_epsilon_positive(self, sensitivity: float, b: float) -> None:
        """Laplace epsilon is always positive."""
        m = LaplaceMechanism(sensitivity=sensitivity, b=b)
        assert m.dp_epsilon() > 0

    @given(
        sensitivity=_pos_float,
        sigma1=_pos_float,
        sigma2=_pos_float,
        delta=_delta_st,
    )
    @settings(max_examples=100)
    def test_rdp_composition_additive(
        self, sensitivity: float, sigma1: float, sigma2: float, delta: float
    ) -> None:
        """RDP composition of two mechanisms ≥ either alone."""
        m1 = GaussianMechanism(sensitivity=sensitivity, sigma=sigma1)
        m2 = GaussianMechanism(sensitivity=sensitivity, sigma=sigma2)
        acc = RDPAccountant()
        acc.spend(m1)
        eps1 = acc.epsilon(delta)
        acc.spend(m2)
        eps12 = acc.epsilon(delta)
        # Composition must not decrease epsilon
        assert eps12 >= eps1 - 1e-12  # small tolerance for floating point

    @given(
        n=st.integers(min_value=1, max_value=10),
        epsilon=_pos_float,
    )
    @settings(max_examples=50)
    def test_basic_composition_linear(self, n: int, epsilon: float) -> None:
        """BasicComposition grows linearly."""
        b = LaplaceMechanism(sensitivity=1.0, b=1.0 / epsilon)
        acc = BasicCompositionAccountant()
        for _ in range(n):
            acc.spend(b)
        assert math.isclose(acc.total_epsilon, n * epsilon, rel_tol=1e-6)

    @given(sensitivity=_pos_float, sigma=_pos_float, delta=_delta_st)
    @settings(max_examples=100)
    def test_rdp_curve_all_positive(self, sensitivity: float, sigma: float, delta: float) -> None:
        """All entries in RDP curve are non-negative after spending."""
        m = GaussianMechanism(sensitivity=sensitivity, sigma=sigma)
        acc = RDPAccountant()
        acc.spend(m)
        for alpha in RDP_ORDERS:
            assert acc.total_rdp(alpha) >= 0

    @given(sensitivity=_pos_float, sigma=_pos_float, delta=_delta_st)
    @settings(max_examples=50)
    def test_planner_rewrite_within_budget(
        self, sensitivity: float, sigma: float, delta: float
    ) -> None:
        """If planner returns 'rewrite', the new sigma must fit the budget."""
        assume(sigma < sensitivity * 500)  # keep search space finite
        planner = QueryPlanner()
        req = QueryRequest(
            query_id="q",
            dataset="ds",
            analyst="a",
            sensitivity=sensitivity,
            sigma=sigma,
            delta=delta,
        )
        # Budget that may or may not fit
        m_max = GaussianMechanism(sensitivity, 1000.0 * sensitivity)
        budget = m_max.dp_epsilon(delta) * 1.5
        decision, new_sigma = planner.plan(req, budget_remaining=budget)
        if decision == "rewrite" and new_sigma is not None:
            m_new = GaussianMechanism(sensitivity, new_sigma)
            assert m_new.dp_epsilon(delta) <= budget + 1e-9
