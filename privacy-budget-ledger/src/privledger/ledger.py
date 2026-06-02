"""BudgetLedger: tracks privacy spend per (dataset, analyst) key."""

from __future__ import annotations

from dataclasses import dataclass, field

from privledger.accountants import BasicCompositionAccountant, RDPAccountant, ZCDPAccountant
from privledger.mechanisms import GaussianMechanism, LaplaceMechanism

Mechanism = GaussianMechanism | LaplaceMechanism


@dataclass
class _AnalystBudget:
    """Internal per-(dataset, analyst) budget container."""

    epsilon_limit: float
    basic: BasicCompositionAccountant = field(default_factory=BasicCompositionAccountant)
    rdp: RDPAccountant = field(default_factory=RDPAccountant)
    zcdp: ZCDPAccountant = field(default_factory=ZCDPAccountant)


@dataclass
class BudgetLedger:
    """Tracks differential privacy spend per (dataset, analyst) key.

    Each (dataset, analyst) pair is allocated a global epsilon budget.
    Three accountants are maintained simultaneously; a query is rejected
    if *any* accountant would exceed the budget.
    """

    default_epsilon_limit: float = 10.0
    default_delta: float = 1e-6

    _budgets: dict[tuple[str, str], _AnalystBudget] = field(default_factory=dict, init=False)

    def _get_or_create(
        self, dataset: str, analyst: str, epsilon_limit: float | None = None
    ) -> _AnalystBudget:
        key = (dataset, analyst)
        if key not in self._budgets:
            limit = epsilon_limit if epsilon_limit is not None else self.default_epsilon_limit
            self._budgets[key] = _AnalystBudget(epsilon_limit=limit)
        return self._budgets[key]

    def set_limit(self, dataset: str, analyst: str, epsilon_limit: float) -> None:
        """Set (or update) the epsilon budget for a (dataset, analyst) pair."""
        key = (dataset, analyst)
        if key in self._budgets:
            self._budgets[key].epsilon_limit = epsilon_limit
        else:
            self._budgets[key] = _AnalystBudget(epsilon_limit=epsilon_limit)

    def can_spend(
        self,
        mechanism: Mechanism,
        *,
        dataset: str,
        analyst: str,
        delta: float | None = None,
    ) -> bool:
        """Return True if all three accountants can afford *mechanism*.

        Does NOT modify the ledger state.
        """
        d = delta if delta is not None else self.default_delta
        budget = self._get_or_create(dataset, analyst)

        if not budget.basic.can_afford(mechanism, budget.epsilon_limit, delta=d):
            return False
        if not budget.rdp.can_afford(mechanism, budget.epsilon_limit, delta=d):
            return False
        if not budget.zcdp.can_afford(mechanism, budget.epsilon_limit, delta=d):
            return False
        return True

    def spend(
        self,
        mechanism: Mechanism,
        query_id: str,
        *,
        dataset: str,
        analyst: str,
        delta: float | None = None,
    ) -> None:
        """Record spend for *query_id* against all three accountants.

        Raises RuntimeError if budget is exceeded (check first with can_spend).
        """
        d = delta if delta is not None else self.default_delta
        if not self.can_spend(mechanism, dataset=dataset, analyst=analyst, delta=d):
            raise RuntimeError(f"Budget exceeded for ({dataset!r}, {analyst!r}): query {query_id}")
        budget = self._get_or_create(dataset, analyst)
        budget.basic.spend(mechanism, d)
        budget.rdp.spend(mechanism)
        budget.zcdp.spend(mechanism, d)

    def remaining_epsilon(
        self,
        *,
        dataset: str,
        analyst: str,
        accountant: str = "basic",
        delta: float | None = None,
    ) -> float:
        """Return remaining epsilon budget (limit minus spent) for one accountant type.

        *accountant* must be one of ``"basic"``, ``"rdp"``, or ``"zcdp"``.
        """
        d = delta if delta is not None else self.default_delta
        budget = self._get_or_create(dataset, analyst)
        if accountant == "basic":
            return budget.epsilon_limit - budget.basic.epsilon()
        elif accountant == "rdp":
            return budget.epsilon_limit - budget.rdp.epsilon(d)
        elif accountant == "zcdp":
            return budget.epsilon_limit - budget.zcdp.epsilon(d)
        else:
            raise ValueError(f"Unknown accountant: {accountant!r}")

    def reset(self, *, dataset: str, analyst: str) -> None:
        """Reset all accountants for a (dataset, analyst) pair."""
        key = (dataset, analyst)
        if key in self._budgets:
            limit = self._budgets[key].epsilon_limit
            self._budgets[key] = _AnalystBudget(epsilon_limit=limit)

    def reset_all(self) -> None:
        """Reset all accountants for every pair."""
        for key, bud in self._budgets.items():
            self._budgets[key] = _AnalystBudget(epsilon_limit=bud.epsilon_limit)

    def status(
        self,
        *,
        dataset: str,
        analyst: str,
        delta: float | None = None,
    ) -> dict[str, float]:
        """Return a dict with spent/remaining for each accountant."""
        d = delta if delta is not None else self.default_delta
        budget = self._get_or_create(dataset, analyst)
        return {
            "epsilon_limit": budget.epsilon_limit,
            "basic_spent": budget.basic.epsilon(),
            "rdp_spent": budget.rdp.epsilon(d),
            "zcdp_spent": budget.zcdp.epsilon(d),
            "basic_remaining": budget.epsilon_limit - budget.basic.epsilon(),
            "rdp_remaining": budget.epsilon_limit - budget.rdp.epsilon(d),
            "zcdp_remaining": budget.epsilon_limit - budget.zcdp.epsilon(d),
        }

    @property
    def keys(self) -> list[tuple[str, str]]:
        """Return all (dataset, analyst) keys currently tracked."""
        return list(self._budgets.keys())
