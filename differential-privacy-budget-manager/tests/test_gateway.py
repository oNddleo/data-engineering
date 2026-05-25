"""Tests for QueryGateway budget tracking and exhaustion policies."""

from __future__ import annotations

import random

import pytest

from dpbudget.gateway import QueryGateway
from dpbudget.registry import AnalystRegistry, BudgetRegistry, DatasetRegistry
from dpbudget.schema import (
    Analyst,
    Dataset,
    ExhaustionPolicy,
    Mechanism,
    QueryRequest,
    QueryStatus,
)


def _make_gateway(
    epsilon: float = 2.0,
    policy: ExhaustionPolicy = ExhaustionPolicy.BLOCK,
    mechanism: Mechanism = Mechanism.LAPLACE,
    seed: int = 42,
) -> QueryGateway:
    rng = random.Random(seed)
    datasets = DatasetRegistry()
    analysts = AnalystRegistry()
    budgets = BudgetRegistry()
    datasets.register(Dataset("ds", "Demo Dataset", sensitivity=1.0))
    analysts.register(Analyst("alice", "Alice"))
    budgets.allocate("ds", "alice", epsilon=epsilon, policy=policy, mechanism=mechanism)
    return QueryGateway(datasets, analysts, budgets, rng)


def _req(
    eps: float = 0.5,
    mechanism: Mechanism = Mechanism.LAPLACE,
    delta: float = 0.0,
) -> QueryRequest:
    return QueryRequest(
        dataset_id="ds",
        analyst_id="alice",
        true_result=100.0,
        epsilon_requested=eps,
        delta_requested=delta,
        mechanism=mechanism,
    )


class TestBasicExecution:
    def test_allowed_query_returns_noisy_result(self) -> None:
        gw = _make_gateway()
        resp = gw.execute(_req(0.5))
        assert resp.status == QueryStatus.ALLOWED
        assert resp.result is not None
        assert resp.noise_added is not None

    def test_budget_debited(self) -> None:
        gw = _make_gateway(epsilon=2.0)
        gw.execute(_req(0.5))
        alloc = gw._budgets.require("ds", "alice")
        assert abs(alloc.consumed_epsilon - 0.5) < 1e-9
        assert abs(alloc.remaining_epsilon - 1.5) < 1e-9

    def test_multiple_queries_accumulate(self) -> None:
        gw = _make_gateway(epsilon=2.0)
        for _ in range(4):
            gw.execute(_req(0.4))
        alloc = gw._budgets.require("ds", "alice")
        assert abs(alloc.consumed_epsilon - 1.6) < 1e-9

    def test_audit_log_grows(self) -> None:
        gw = _make_gateway()
        gw.execute(_req(0.5))
        gw.execute(_req(0.5))
        assert len(gw.audit_log()) == 2

    def test_query_id_unique(self) -> None:
        gw = _make_gateway()
        r1 = gw.execute(_req(0.5))
        r2 = gw.execute(_req(0.5))
        assert r1.query_id != r2.query_id


class TestBlockPolicy:
    def test_query_blocked_when_exhausted(self) -> None:
        gw = _make_gateway(epsilon=0.3, policy=ExhaustionPolicy.BLOCK)
        gw.execute(_req(0.3))  # exhaust
        resp = gw.execute(_req(0.3))
        assert resp.status == QueryStatus.BLOCKED
        assert resp.result is None

    def test_blocked_query_not_debited(self) -> None:
        gw = _make_gateway(epsilon=0.3, policy=ExhaustionPolicy.BLOCK)
        gw.execute(_req(0.3))
        before = gw._budgets.require("ds", "alice").consumed_epsilon
        gw.execute(_req(0.3))
        after = gw._budgets.require("ds", "alice").consumed_epsilon
        assert abs(before - after) < 1e-9

    def test_insufficient_budget_blocked(self) -> None:
        gw = _make_gateway(epsilon=0.4, policy=ExhaustionPolicy.BLOCK)
        resp = gw.execute(_req(1.0))  # needs more than available
        assert resp.status == QueryStatus.BLOCKED


class TestInjectNoisePolicy:
    def test_inject_policy_still_returns_result(self) -> None:
        gw = _make_gateway(epsilon=0.3, policy=ExhaustionPolicy.INJECT_NOISE)
        gw.execute(_req(0.3))  # exhaust
        resp = gw.execute(_req(0.3))
        # inject_noise may allow with very tiny epsilon (≥1e-9)
        assert resp.status == QueryStatus.ALLOWED
        assert resp.result is not None


class TestGaussianMechanism:
    def test_gaussian_query_allowed(self) -> None:
        rng = random.Random(0)
        datasets = DatasetRegistry()
        analysts = AnalystRegistry()
        budgets = BudgetRegistry()
        datasets.register(Dataset("ds", "D", sensitivity=1.0))
        analysts.register(Analyst("a", "A"))
        budgets.allocate("ds", "a", epsilon=2.0, delta=1e-3, mechanism=Mechanism.GAUSSIAN)
        gw = QueryGateway(datasets, analysts, budgets, rng)
        resp = gw.execute(
            QueryRequest("ds", "a", 50.0, 0.5, delta_requested=1e-3, mechanism=Mechanism.GAUSSIAN)
        )
        assert resp.status == QueryStatus.ALLOWED
        assert resp.delta_consumed > 0


class TestAuditLog:
    def test_log_for_analyst(self) -> None:
        gw = _make_gateway()
        gw.execute(_req(0.5))
        entries = gw.log_for("alice")
        assert len(entries) == 1

    def test_log_for_dataset(self) -> None:
        gw = _make_gateway()
        gw.execute(_req(0.5))
        entries = gw.log_for_dataset("ds")
        assert len(entries) == 1

    def test_unknown_analyst_raises(self) -> None:
        gw = _make_gateway()
        req = QueryRequest("ds", "unknown", 10.0, 0.1)
        with pytest.raises(KeyError):
            gw.execute(req)

    def test_unknown_dataset_raises(self) -> None:
        gw = _make_gateway()
        req = QueryRequest("nope", "alice", 10.0, 0.1)
        with pytest.raises(KeyError):
            gw.execute(req)
