"""Query gateway: validates requests, debits budget, adds DP noise."""

from __future__ import annotations

import random
import uuid
from typing import TYPE_CHECKING

from dpbudget.mechanisms import apply_gaussian, apply_laplace
from dpbudget.schema import (
    Mechanism,
    QueryLogEntry,
    QueryRequest,
    QueryResponse,
    QueryStatus,
)

if TYPE_CHECKING:
    from dpbudget.registry import AnalystRegistry, BudgetRegistry, DatasetRegistry


class QueryGateway:
    """Central gateway that processes DP queries against registered budgets.

    Maintains an immutable audit log of every execution.
    """

    def __init__(
        self,
        datasets: DatasetRegistry,
        analysts: AnalystRegistry,
        budgets: BudgetRegistry,
        rng: random.Random | None = None,
    ) -> None:
        self._datasets = datasets
        self._analysts = analysts
        self._budgets = budgets
        self._rng = rng or random.Random()
        self._log: list[QueryLogEntry] = []

    # ── Query execution ───────────────────────────────────────────────────────

    def execute(self, req: QueryRequest) -> QueryResponse:
        """Execute a DP query, debit budget, and return a noisy result."""
        # Validate references
        self._datasets.require(req.dataset_id)
        self._analysts.require(req.analyst_id)
        alloc = self._budgets.require(req.dataset_id, req.analyst_id)

        mechanism = req.mechanism or alloc.default_mechanism
        sensitivity = (
            req.sensitivity
            if req.sensitivity is not None
            else self._datasets.require(req.dataset_id).sensitivity
        )
        epsilon_cost = req.epsilon_requested
        delta_cost = req.delta_requested if mechanism == Mechanism.GAUSSIAN else 0.0

        # ── Exhaustion / partial-budget handling ──────────────────────────────
        if alloc.is_exhausted or alloc.remaining_epsilon < epsilon_cost:
            if alloc.exhaustion_policy.value == "block":
                entry = self._make_log(
                    req,
                    mechanism,
                    sensitivity,
                    QueryStatus.BLOCKED,
                    None,
                    None,
                    0.0,
                    0.0,
                    alloc.remaining_epsilon,
                )
                self._log.append(entry)
                return QueryResponse(
                    query_id=entry.query_id,
                    status=QueryStatus.BLOCKED,
                    result=None,
                    noise_added=None,
                    epsilon_consumed=0.0,
                    delta_consumed=0.0,
                    budget_remaining=alloc.remaining_epsilon,
                    mechanism_used=mechanism,
                    message=(
                        "Privacy budget exhausted. Query blocked."
                        if alloc.is_exhausted
                        else f"Insufficient budget: need ε={epsilon_cost}, "
                        f"remaining ε={alloc.remaining_epsilon:.6f}."
                    ),
                )
            else:
                # inject_noise: use whatever remains (→ huge noise)
                epsilon_cost = max(alloc.remaining_epsilon, 1e-9)
                if mechanism == Mechanism.GAUSSIAN:
                    delta_cost = max(alloc.remaining_delta, 1e-9)
                else:
                    delta_cost = 0.0

        # ── Apply noise ───────────────────────────────────────────────────────
        if mechanism == Mechanism.GAUSSIAN:
            noisy, noise = apply_gaussian(
                req.true_result, sensitivity, epsilon_cost, delta_cost, self._rng
            )
        else:
            noisy, noise = apply_laplace(req.true_result, sensitivity, epsilon_cost, self._rng)

        # ── Debit budget ──────────────────────────────────────────────────────
        alloc.consumed_epsilon = round(alloc.consumed_epsilon + epsilon_cost, 10)
        alloc.consumed_delta = round(alloc.consumed_delta + delta_cost, 10)

        entry = self._make_log(
            req,
            mechanism,
            sensitivity,
            QueryStatus.ALLOWED,
            noisy,
            noise,
            epsilon_cost,
            delta_cost,
            alloc.remaining_epsilon,
        )
        self._log.append(entry)

        return QueryResponse(
            query_id=entry.query_id,
            status=QueryStatus.ALLOWED,
            result=noisy,
            noise_added=noise,
            epsilon_consumed=epsilon_cost,
            delta_consumed=delta_cost,
            budget_remaining=alloc.remaining_epsilon,
            mechanism_used=mechanism,
            message="Query executed with differential privacy.",
        )

    # ── Audit log ─────────────────────────────────────────────────────────────

    def audit_log(self) -> list[QueryLogEntry]:
        return list(self._log)

    def log_for(self, analyst_id: str) -> list[QueryLogEntry]:
        return [e for e in self._log if e.analyst_id == analyst_id]

    def log_for_dataset(self, dataset_id: str) -> list[QueryLogEntry]:
        return [e for e in self._log if e.dataset_id == dataset_id]

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _make_log(
        req: QueryRequest,
        mechanism: Mechanism,
        sensitivity: float,
        status: QueryStatus,
        noisy: float | None,
        noise: float | None,
        epsilon_consumed: float,
        delta_consumed: float,
        remaining: float,
    ) -> QueryLogEntry:
        return QueryLogEntry(
            query_id=str(uuid.uuid4()),
            dataset_id=req.dataset_id,
            analyst_id=req.analyst_id,
            query_text=req.query_text,
            true_result=req.true_result,
            noisy_result=noisy,
            noise_added=noise,
            epsilon_requested=req.epsilon_requested,
            delta_requested=req.delta_requested,
            epsilon_consumed=epsilon_consumed,
            delta_consumed=delta_consumed,
            sensitivity=sensitivity,
            mechanism_used=mechanism,
            status=status,
            budget_remaining_after=remaining,
        )
