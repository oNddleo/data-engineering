"""AlertEngine: rule-based alert generation for systemic risk metrics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from riskmonitor.analyzer import RiskReport


class Severity(str, Enum):
    """Alert severity levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    INFO = "INFO"


@dataclass
class Alert:
    """A single risk alert."""

    severity: Severity
    rule: str
    message: str
    value: float

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable representation."""
        return {
            "severity": self.severity.value,
            "rule": self.rule,
            "message": self.message,
            "value": self.value,
        }


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

_HHI_CRITICAL = 0.25
_CYCLE_NOTIONAL_CRITICAL = 500_000_000.0  # 500 M
_GINI_HIGH = 0.7
_BETWEENNESS_HIGH = 0.3
_HHI_HIGH = 0.18
_CASCADE_SIZE_HIGH = 5
_GINI_MEDIUM = 0.5
_CYCLE_COUNT_MEDIUM = 3
_BETWEENNESS_MEDIUM = 0.2
_HHI_INFO = 0.1


class AlertEngine:
    """Evaluates a :class:`~riskmonitor.analyzer.RiskReport` against risk rules.

    Rules (in priority order)
    -------------------------
    CRITICAL:
    - HHI > 0.25              → market highly concentrated
    - max cycle notional > 500 M → large circular exposure

    HIGH:
    - Gini > 0.7              → extreme exposure inequality
    - betweenness_max > 0.3   → single node is systemically critical
    - cascade_size >= 5       → systemic contagion risk
    - HHI > 0.18              → moderately concentrated

    MEDIUM:
    - Gini > 0.5              → elevated inequality
    - cycle_count >= 3        → multiple circular exposures
    - betweenness_max > 0.2   → elevated centrality

    INFO:
    - HHI > 0.1               → mild concentration
    - any cycles exist        → circular exposures detected
    """

    def evaluate(self, report: RiskReport) -> list[Alert]:
        """Evaluate *report* and return all triggered alerts."""
        alerts: list[Alert] = []

        # CRITICAL rules
        if report.hhi > _HHI_CRITICAL:
            alerts.append(
                Alert(
                    severity=Severity.CRITICAL,
                    rule="HHI_CRITICAL",
                    message=(
                        f"Market concentration is critically high: HHI={report.hhi:.4f} "
                        f"(threshold={_HHI_CRITICAL})"
                    ),
                    value=report.hhi,
                )
            )

        if report.max_cycle_notional > _CYCLE_NOTIONAL_CRITICAL:
            alerts.append(
                Alert(
                    severity=Severity.CRITICAL,
                    rule="CYCLE_NOTIONAL_CRITICAL",
                    message=(
                        f"Circular exposure notional exceeds 500 M: "
                        f"{report.max_cycle_notional:,.0f} "
                        f"(threshold={_CYCLE_NOTIONAL_CRITICAL:,.0f})"
                    ),
                    value=report.max_cycle_notional,
                )
            )

        # HIGH rules
        if report.gini > _GINI_HIGH:
            alerts.append(
                Alert(
                    severity=Severity.HIGH,
                    rule="GINI_HIGH",
                    message=(
                        f"Exposure distribution extremely unequal: Gini={report.gini:.4f} "
                        f"(threshold={_GINI_HIGH})"
                    ),
                    value=report.gini,
                )
            )

        if report.betweenness_max > _BETWEENNESS_HIGH:
            alerts.append(
                Alert(
                    severity=Severity.HIGH,
                    rule="BETWEENNESS_HIGH",
                    message=(
                        f"Node '{report.betweenness_max_node}' is systemically critical: "
                        f"betweenness={report.betweenness_max:.4f} "
                        f"(threshold={_BETWEENNESS_HIGH})"
                    ),
                    value=report.betweenness_max,
                )
            )

        cascade_size = report.cascade.size if report.cascade else 0
        if cascade_size >= _CASCADE_SIZE_HIGH:
            alerts.append(
                Alert(
                    severity=Severity.HIGH,
                    rule="CASCADE_SIZE_HIGH",
                    message=(
                        f"Cascade from '{report.betweenness_max_node}' reaches "
                        f"{cascade_size} nodes (threshold={_CASCADE_SIZE_HIGH})"
                    ),
                    value=float(cascade_size),
                )
            )

        if _HHI_HIGH < report.hhi <= _HHI_CRITICAL:
            alerts.append(
                Alert(
                    severity=Severity.HIGH,
                    rule="HHI_HIGH",
                    message=(
                        f"Market concentration is high: HHI={report.hhi:.4f} "
                        f"(threshold={_HHI_HIGH})"
                    ),
                    value=report.hhi,
                )
            )

        # MEDIUM rules
        if _GINI_MEDIUM < report.gini <= _GINI_HIGH:
            alerts.append(
                Alert(
                    severity=Severity.MEDIUM,
                    rule="GINI_MEDIUM",
                    message=(
                        f"Exposure distribution is unequal: Gini={report.gini:.4f} "
                        f"(threshold={_GINI_MEDIUM})"
                    ),
                    value=report.gini,
                )
            )

        if len(report.cycles) >= _CYCLE_COUNT_MEDIUM:
            alerts.append(
                Alert(
                    severity=Severity.MEDIUM,
                    rule="CYCLE_COUNT_MEDIUM",
                    message=(
                        f"Multiple circular exposures detected: {len(report.cycles)} cycles "
                        f"(threshold={_CYCLE_COUNT_MEDIUM})"
                    ),
                    value=float(len(report.cycles)),
                )
            )

        if _BETWEENNESS_MEDIUM < report.betweenness_max <= _BETWEENNESS_HIGH:
            alerts.append(
                Alert(
                    severity=Severity.MEDIUM,
                    rule="BETWEENNESS_MEDIUM",
                    message=(
                        f"Elevated centrality on '{report.betweenness_max_node}': "
                        f"betweenness={report.betweenness_max:.4f} "
                        f"(threshold={_BETWEENNESS_MEDIUM})"
                    ),
                    value=report.betweenness_max,
                )
            )

        # INFO rules
        if _HHI_INFO < report.hhi <= _HHI_HIGH:
            alerts.append(
                Alert(
                    severity=Severity.INFO,
                    rule="HHI_INFO",
                    message=(
                        f"Mild market concentration: HHI={report.hhi:.4f} "
                        f"(threshold={_HHI_INFO})"
                    ),
                    value=report.hhi,
                )
            )

        if report.cycles and report.max_cycle_notional <= _CYCLE_NOTIONAL_CRITICAL:
            alerts.append(
                Alert(
                    severity=Severity.INFO,
                    rule="CYCLES_EXIST",
                    message=(
                        f"{len(report.cycles)} circular exposure(s) detected; "
                        f"max notional={report.max_cycle_notional:,.0f}"
                    ),
                    value=float(len(report.cycles)),
                )
            )

        return alerts
