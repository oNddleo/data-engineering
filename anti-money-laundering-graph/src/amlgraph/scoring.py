"""Per-account risk scoring from a bag of AML alerts.

Score is a non-negative integer assembled from:

* A flat **a-priori** bump per :class:`RiskFlag` on the account
  (PEP/SANCTIONED/MULE_SUSPECTED/...).
* Severity-weighted contributions from each alert that touches the
  account — either as ``primary_account`` or as a member of
  ``related_accounts``.

The output is a ``dict[account_id, int]`` plus a tuple of the top-N
risky accounts. Production swaps this for a trained model;
the rule-based version exists so the rest of the pipeline can be
exercised end-to-end with explainable outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from amlgraph.alerts import AlertKind, Severity
from amlgraph.schema import RiskFlag

if TYPE_CHECKING:
    from collections.abc import Iterable

    from amlgraph.alerts import AMLAlert
    from amlgraph.graph import TransactionGraph


SEVERITY_POINTS: dict[Severity, int] = {
    Severity.INFO: 5,
    Severity.WARN: 25,
    Severity.CRIT: 75,
}

KIND_MULTIPLIER: dict[AlertKind, float] = {
    AlertKind.FAN_OUT: 1.0,
    AlertKind.FAN_IN: 1.0,
    AlertKind.LAYERING_CHAIN: 1.5,
    AlertKind.ROUND_TRIP: 1.5,
    AlertKind.STRUCTURED_DEPOSIT: 1.2,
}

RISK_FLAG_POINTS: dict[RiskFlag, int] = {
    RiskFlag.PEP: 30,
    RiskFlag.SANCTIONED: 100,
    RiskFlag.MULE_SUSPECTED: 50,
    RiskFlag.HIGH_RISK_JURISDICTION: 20,
    RiskFlag.PRIOR_SAR: 40,
}


@dataclass(frozen=True, slots=True)
class RankedAccount:
    """One row in the top-N risk list."""

    account_id: str
    score: int


def score_accounts(
    graph: TransactionGraph,
    alerts: Iterable[AMLAlert],
) -> dict[str, int]:
    """Compute a per-account risk score from a-priori flags + alert hits.

    Every account that appears anywhere — node, edge endpoint, alert
    relation — gets at least a zero entry, so callers can render a
    stable table without `KeyError`.
    """
    scores: dict[str, int] = dict.fromkeys(graph.all_known_account_ids(), 0)

    # A-priori from RiskFlag.
    for account in graph.all_accounts():
        scores.setdefault(account.account_id, 0)
        for flag in account.risk_flags:
            scores[account.account_id] += RISK_FLAG_POINTS[flag]

    # Alert contributions.
    for alert in alerts:
        delta = int(SEVERITY_POINTS[alert.severity] * KIND_MULTIPLIER[alert.kind])
        scores[alert.primary_account] = scores.get(alert.primary_account, 0) + delta
        for rel in alert.related_accounts:
            # Related accounts get half-credit; they're implicated but not the centre.
            scores[rel] = scores.get(rel, 0) + delta // 2
    return scores


def top_n(scores: dict[str, int], n: int = 10) -> list[RankedAccount]:
    """Return the highest-scoring ``n`` accounts in descending order."""
    if n <= 0:
        raise ValueError("n must be > 0")
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [RankedAccount(a, s) for a, s in ranked[:n] if s > 0]


__all__ = [
    "KIND_MULTIPLIER",
    "RISK_FLAG_POINTS",
    "SEVERITY_POINTS",
    "RankedAccount",
    "score_accounts",
    "top_n",
]
