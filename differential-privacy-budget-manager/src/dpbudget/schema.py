"""Domain types for the differential-privacy budget manager."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class Mechanism(str, enum.Enum):
    """Noise mechanism."""

    LAPLACE = "laplace"
    GAUSSIAN = "gaussian"


class ExhaustionPolicy(str, enum.Enum):
    """What to do when a budget is exhausted."""

    BLOCK = "block"  # reject query
    INJECT_NOISE = "inject_noise"  # add maximum noise (remaining ε → 0⁺)


class QueryStatus(str, enum.Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"


# ── Dataset ───────────────────────────────────────────────────────────────────


@dataclass
class Dataset:
    """A registered dataset with a default sensitivity."""

    dataset_id: str
    name: str
    sensitivity: float = 1.0
    description: str = ""


# ── Analyst ───────────────────────────────────────────────────────────────────


@dataclass
class Analyst:
    """An analyst who issues queries."""

    analyst_id: str
    name: str
    email: str = ""


# ── Budget allocation ─────────────────────────────────────────────────────────


@dataclass
class BudgetAllocation:
    """Per-(dataset, analyst) privacy budget."""

    dataset_id: str
    analyst_id: str
    epsilon_total: float
    delta_total: float = 0.0
    consumed_epsilon: float = 0.0
    consumed_delta: float = 0.0
    exhaustion_policy: ExhaustionPolicy = ExhaustionPolicy.BLOCK
    default_mechanism: Mechanism = Mechanism.LAPLACE

    @property
    def remaining_epsilon(self) -> float:
        return max(0.0, round(self.epsilon_total - self.consumed_epsilon, 10))

    @property
    def remaining_delta(self) -> float:
        return max(0.0, round(self.delta_total - self.consumed_delta, 10))

    @property
    def is_exhausted(self) -> bool:
        return self.remaining_epsilon <= 0.0


# ── Query request / response ──────────────────────────────────────────────────


@dataclass
class QueryRequest:
    """A single differentially-private query."""

    dataset_id: str
    analyst_id: str
    true_result: float
    epsilon_requested: float
    delta_requested: float = 0.0
    sensitivity: float | None = None
    mechanism: Mechanism | None = None
    query_text: str = ""


@dataclass
class QueryResponse:
    """Result of executing a DP query."""

    query_id: str
    status: QueryStatus
    result: float | None
    noise_added: float | None
    epsilon_consumed: float
    delta_consumed: float
    budget_remaining: float
    mechanism_used: Mechanism
    message: str = ""


# ── Audit log entry ───────────────────────────────────────────────────────────


@dataclass
class QueryLogEntry:
    """Immutable record of one query execution."""

    query_id: str
    dataset_id: str
    analyst_id: str
    query_text: str
    true_result: float
    noisy_result: float | None
    noise_added: float | None
    epsilon_requested: float
    delta_requested: float
    epsilon_consumed: float
    delta_consumed: float
    sensitivity: float
    mechanism_used: Mechanism
    status: QueryStatus
    budget_remaining_after: float
    tags: list[str] = field(default_factory=list)
