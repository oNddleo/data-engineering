"""In-memory registries for datasets, analysts, and budget allocations."""

from __future__ import annotations

from dpbudget.schema import Analyst, BudgetAllocation, Dataset, ExhaustionPolicy, Mechanism


class DatasetRegistry:
    """CRUD for datasets."""

    def __init__(self) -> None:
        self._store: dict[str, Dataset] = {}

    def register(self, dataset: Dataset) -> None:
        self._store[dataset.dataset_id] = dataset

    def get(self, dataset_id: str) -> Dataset | None:
        return self._store.get(dataset_id)

    def require(self, dataset_id: str) -> Dataset:
        ds = self.get(dataset_id)
        if ds is None:
            raise KeyError(f"Dataset {dataset_id!r} not found")
        return ds

    def all(self) -> list[Dataset]:
        return list(self._store.values())


class AnalystRegistry:
    """CRUD for analysts."""

    def __init__(self) -> None:
        self._store: dict[str, Analyst] = {}

    def register(self, analyst: Analyst) -> None:
        self._store[analyst.analyst_id] = analyst

    def get(self, analyst_id: str) -> Analyst | None:
        return self._store.get(analyst_id)

    def require(self, analyst_id: str) -> Analyst:
        a = self.get(analyst_id)
        if a is None:
            raise KeyError(f"Analyst {analyst_id!r} not found")
        return a

    def all(self) -> list[Analyst]:
        return list(self._store.values())


class BudgetRegistry:
    """Per-(dataset, analyst) budget allocations."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], BudgetAllocation] = {}

    def allocate(
        self,
        dataset_id: str,
        analyst_id: str,
        epsilon: float,
        delta: float = 0.0,
        policy: ExhaustionPolicy = ExhaustionPolicy.BLOCK,
        mechanism: Mechanism = Mechanism.LAPLACE,
    ) -> BudgetAllocation:
        alloc = BudgetAllocation(
            dataset_id=dataset_id,
            analyst_id=analyst_id,
            epsilon_total=epsilon,
            delta_total=delta,
            exhaustion_policy=policy,
            default_mechanism=mechanism,
        )
        self._store[(dataset_id, analyst_id)] = alloc
        return alloc

    def get(self, dataset_id: str, analyst_id: str) -> BudgetAllocation | None:
        return self._store.get((dataset_id, analyst_id))

    def require(self, dataset_id: str, analyst_id: str) -> BudgetAllocation:
        alloc = self.get(dataset_id, analyst_id)
        if alloc is None:
            raise KeyError(f"No budget for analyst={analyst_id!r} on dataset={dataset_id!r}")
        return alloc

    def reset(self, dataset_id: str, analyst_id: str) -> None:
        alloc = self.require(dataset_id, analyst_id)
        alloc.consumed_epsilon = 0.0
        alloc.consumed_delta = 0.0

    def adjust(
        self, dataset_id: str, analyst_id: str, new_epsilon: float, new_delta: float = 0.0
    ) -> BudgetAllocation:
        alloc = self.require(dataset_id, analyst_id)
        alloc.epsilon_total = new_epsilon
        alloc.delta_total = new_delta
        return alloc

    def all(self) -> list[BudgetAllocation]:
        return list(self._store.values())
