"""Monitor engine — applies a list of rules in order and collects alerts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from n247mon.alerts import Alert, AlertKind, Severity
    from n247mon.rules import Rule
    from n247mon.schema import Transaction


@dataclass(slots=True)
class EngineStats:
    """Running tally the engine maintains while consuming a stream."""

    txns_seen: int = 0
    alerts_fired: int = 0
    alerts_by_kind: dict[AlertKind, int] = field(default_factory=dict)
    alerts_by_severity: dict[Severity, int] = field(default_factory=dict)

    def record(self, alerts: Iterable[Alert]) -> None:
        for a in alerts:
            self.alerts_fired += 1
            self.alerts_by_kind[a.kind] = self.alerts_by_kind.get(a.kind, 0) + 1
            self.alerts_by_severity[a.severity] = self.alerts_by_severity.get(a.severity, 0) + 1


class MonitorEngine:
    """Apply ``rules`` to each transaction in turn.

    The engine is intentionally a one-line orchestrator — it owns
    the rule list and a stats counter, nothing else. The interesting
    logic lives in the rules.
    """

    def __init__(self, rules: list[Rule]) -> None:
        if not rules:
            raise ValueError("MonitorEngine requires at least one rule")
        self._rules: list[Rule] = list(rules)
        self.stats = EngineStats()

    @property
    def rules(self) -> list[Rule]:
        return list(self._rules)

    def consume(self, txn: Transaction) -> list[Alert]:
        """Run every rule against ``txn`` and return the flattened alert list."""
        self.stats.txns_seen += 1
        alerts: list[Alert] = []
        for rule in self._rules:
            alerts.extend(rule.consume(txn))
        self.stats.record(alerts)
        return alerts

    def consume_many(self, txns: Iterable[Transaction]) -> list[Alert]:
        """Drain an iterable and return all alerts in input order."""
        out: list[Alert] = []
        for t in txns:
            out.extend(self.consume(t))
        return out


__all__ = ["EngineStats", "MonitorEngine"]
