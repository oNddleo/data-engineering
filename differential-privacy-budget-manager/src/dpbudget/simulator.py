"""Demo simulator: seeds a multi-analyst, multi-dataset scenario."""

from __future__ import annotations

import random

from dpbudget.gateway import QueryGateway
from dpbudget.registry import AnalystRegistry, BudgetRegistry, DatasetRegistry
from dpbudget.schema import Analyst, Dataset, ExhaustionPolicy, Mechanism, QueryRequest


def build_demo_gateway(seed: int = 42) -> QueryGateway:
    """Return a QueryGateway seeded with demo data (no I/O side effects)."""
    rng = random.Random(seed)
    datasets = DatasetRegistry()
    analysts = AnalystRegistry()
    budgets = BudgetRegistry()

    # Register datasets
    for ds in [
        Dataset("patients", "Patient Records", sensitivity=100.0),
        Dataset("banking", "Banking Transactions", sensitivity=10_000.0),
        Dataset("salaries", "Employee Salaries", sensitivity=200_000.0),
    ]:
        datasets.register(ds)

    # Register analysts
    for a in [
        Analyst("alice", "Alice Chen", "alice@hospital.vn"),
        Analyst("bob", "Bob Nguyen", "bob@bank.vn"),
        Analyst("carol", "Carol Tran", "carol@hr.vn"),
    ]:
        analysts.register(a)

    # Allocate budgets (ε, δ)
    budgets.allocate("patients", "alice", epsilon=3.0, delta=1e-5, mechanism=Mechanism.GAUSSIAN)
    budgets.allocate("banking", "bob", epsilon=2.0, policy=ExhaustionPolicy.INJECT_NOISE)
    budgets.allocate("salaries", "carol", epsilon=1.0)
    budgets.allocate("patients", "bob", epsilon=0.5)

    gw = QueryGateway(datasets, analysts, budgets, rng)
    return gw


def run_demo(seed: int = 42) -> QueryGateway:
    """Run a set of demo queries and return the populated gateway."""
    gw = build_demo_gateway(seed)

    # Alice counts patients with diagnosis = diabetes
    gw.execute(
        QueryRequest(
            "patients",
            "alice",
            true_result=142.0,
            epsilon_requested=0.5,
            delta_requested=1e-5,
            mechanism=Mechanism.GAUSSIAN,
            query_text="SELECT COUNT(*) FROM patients WHERE diagnosis='diabetes'",
        )
    )
    gw.execute(
        QueryRequest(
            "patients",
            "alice",
            true_result=98.0,
            epsilon_requested=0.5,
            delta_requested=1e-5,
            mechanism=Mechanism.GAUSSIAN,
            query_text="SELECT COUNT(*) FROM patients WHERE age > 60",
        )
    )

    # Bob queries banking data with Laplace
    for i in range(3):
        gw.execute(
            QueryRequest(
                "banking",
                "bob",
                true_result=50_000.0 + i * 1000,
                epsilon_requested=0.5,
                query_text=f"SELECT SUM(amount) FROM txn WHERE day={i + 1}",
            )
        )
    # Bob also tries patients (tight budget → block on 2nd)
    gw.execute(
        QueryRequest(
            "patients",
            "bob",
            true_result=10.0,
            epsilon_requested=0.3,
            query_text="SELECT COUNT(*) FROM patients WHERE age < 18",
        )
    )
    gw.execute(
        QueryRequest(
            "patients",
            "bob",
            true_result=5.0,
            epsilon_requested=0.3,
            query_text="SELECT COUNT(*) FROM patients WHERE gender='M'",
        )
    )

    # Carol queries salaries
    gw.execute(
        QueryRequest(
            "salaries",
            "carol",
            true_result=75_000.0,
            epsilon_requested=1.0,
            query_text="SELECT AVG(salary) FROM employees WHERE dept='engineering'",
        )
    )

    return gw
