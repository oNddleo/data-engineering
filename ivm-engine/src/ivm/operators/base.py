"""Base operator for the IVM dataflow graph.

Operators form a DAG.  Each operator:
  1. Receives a batch of Updates from upstream via handle().
  2. Computes an output batch via process() (pure, override in subclasses).
  3. Forwards the output batch to all downstream listeners.

The fluent builder methods (filter, project, group_by, window, join) let you
construct pipelines without manually wiring listeners.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ivm.types import Update


class Operator(ABC):
    """Abstract base class for all IVM dataflow operators."""

    def __init__(self) -> None:
        self._listeners: list[Callable[[list[Update]], None]] = []
        self.name: str | None = None

    # ------------------------------------------------------------------
    # Subclasses implement this
    # ------------------------------------------------------------------

    @abstractmethod
    def process(self, updates: list[Update]) -> list[Update]:
        """Transform input updates into output updates (pure computation)."""
        ...

    # ------------------------------------------------------------------
    # Plumbing
    # ------------------------------------------------------------------

    def handle(self, updates: list[Update]) -> None:
        """Entry point: called by upstream operators or the engine."""
        if not updates:
            return
        out = self.process(updates)
        if out:
            self._emit(out)

    def _emit(self, updates: list[Update]) -> None:
        for fn in self._listeners:
            fn(updates)

    def add_listener(self, fn: Callable[[list[Update]], None]) -> None:
        """Register a downstream listener to receive emitted updates."""
        self._listeners.append(fn)

    # ------------------------------------------------------------------
    # Fluent builder API
    # ------------------------------------------------------------------

    def pipe(self, op: Operator) -> Operator:
        """Wire self → op and return op for chaining."""
        self.add_listener(op.handle)
        return op

    def filter(self, predicate: Callable[[Any], bool]) -> Operator:
        """Attach a FilterOperator that keeps records matching predicate."""
        from ivm.operators.filter import FilterOperator
        return self.pipe(FilterOperator(predicate))

    def project(
        self,
        columns: list[str] | None = None,
        transform: Callable[[Any], Any] | None = None,
    ) -> Operator:
        """Attach a ProjectOperator that reshapes records."""
        from ivm.operators.project import ProjectOperator
        return self.pipe(ProjectOperator(columns, transform))

    def group_by(self, key_columns: list[str], aggregates: dict[str, Any]) -> Operator:
        """Attach a GroupByOperator for incremental aggregation."""
        from ivm.operators.group_by import GroupByOperator
        return self.pipe(GroupByOperator(key_columns, aggregates))

    def window(
        self,
        window_spec: Any,
        aggregates: dict[str, Any] | None = None,
        rank_fns: dict[str, str] | None = None,
    ) -> Operator:
        """Attach a WindowOperator for time or partition windowing."""
        from ivm.operators.window import WindowOperator
        return self.pipe(WindowOperator(window_spec, aggregates or {}, rank_fns or {}))

    def join(
        self,
        right: Operator,
        left_key: Any,
        right_key: Any,
        join_type: str = "inner",
    ) -> Operator:
        """Wire a JoinOperator between self (left) and right."""
        from ivm.operators.join import JoinOperator
        op = JoinOperator(left_key, right_key, join_type)
        self.add_listener(op.handle_left)
        right.add_listener(op.handle_right)
        return op
