"""Five classic AML pattern detectors against :class:`TransactionGraph`.

Each detector is a pure function ``(graph, **params) -> list[AMLAlert]``.
The functions are independent — caller composes them in whatever
order they want (or in parallel).

**Fan-out** — one source account sends to ≥ ``min_distinct_dests``
distinct beneficiaries within ``window_seconds``. The classic
"smurf controller" topology.

**Fan-in** — one destination receives from ≥ ``min_distinct_sources``
distinct senders within ``window_seconds``. The classic "collection
account" topology.

**Layering chain** — a directed path of length ``min_depth`` where
every consecutive hop occurs within ``hop_seconds`` of the previous,
and the *cumulative* path duration is bounded by ``total_seconds``.
Used to obscure the source of funds across multiple hops.

**Round-trip** — DFS finds a cycle of length ≥ 2 that returns to the
same account within ``window_seconds``. Money looping back through
intermediaries is a textbook layering signal.

**Structured deposit** — one destination receives ≥ ``min_count``
incoming transfers in the just-under-threshold band
``(threshold − margin, threshold]`` within ``window_seconds``, from
≥ ``min_distinct_sources`` distinct sources. Distinct from the
real-time monitor's structuring rule (that one is per-initiator);
this one is per-recipient, which catches mule collection patterns.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from amlgraph.alerts import AlertKind, AMLAlert, Severity

if TYPE_CHECKING:
    from amlgraph.graph import TransactionGraph
    from amlgraph.schema import Transaction


# ---------------------------------------------------------------------------
# Fan-out / Fan-in.


def detect_fan_out(
    graph: TransactionGraph,
    *,
    min_distinct_dests: int = 5,
    window_seconds: int = 3600,
) -> list[AMLAlert]:
    """Flag accounts that send to many distinct destinations in a short window."""
    if min_distinct_dests < 2:
        raise ValueError("min_distinct_dests must be >= 2")
    window = timedelta(seconds=window_seconds)
    alerts: list[AMLAlert] = []
    for account_id in sorted(graph.all_known_account_ids()):
        out = sorted(graph.out_edges(account_id), key=lambda t: t.occurred_at)
        if len(out) < min_distinct_dests:
            continue
        # Sliding window — for each anchor edge, look forward.
        for i, anchor in enumerate(out):
            cutoff = anchor.occurred_at + window
            bucket: list[Transaction] = []
            for t in out[i:]:
                if t.occurred_at > cutoff:
                    break
                bucket.append(t)
            dests = {t.to_account for t in bucket}
            if len(dests) >= min_distinct_dests:
                alerts.append(
                    AMLAlert(
                        kind=AlertKind.FAN_OUT,
                        severity=Severity.WARN,
                        primary_account=account_id,
                        related_accounts=tuple(sorted(dests)),
                        total_amount_vnd=sum(t.amount_vnd for t in bucket),
                        detail=(
                            f"sent to {len(dests)} distinct destinations in "
                            f"{window_seconds}s window (threshold {min_distinct_dests})"
                        ),
                        txn_ids=tuple(t.txn_id for t in bucket),
                    )
                )
                break  # one alert per source is enough
    return alerts


def detect_fan_in(
    graph: TransactionGraph,
    *,
    min_distinct_sources: int = 5,
    window_seconds: int = 3600,
) -> list[AMLAlert]:
    """Flag accounts that receive from many distinct senders in a short window."""
    if min_distinct_sources < 2:
        raise ValueError("min_distinct_sources must be >= 2")
    window = timedelta(seconds=window_seconds)
    alerts: list[AMLAlert] = []
    for account_id in sorted(graph.all_known_account_ids()):
        ins = sorted(graph.in_edges(account_id), key=lambda t: t.occurred_at)
        if len(ins) < min_distinct_sources:
            continue
        for i, anchor in enumerate(ins):
            cutoff = anchor.occurred_at + window
            bucket: list[Transaction] = []
            for t in ins[i:]:
                if t.occurred_at > cutoff:
                    break
                bucket.append(t)
            sources = {t.from_account for t in bucket}
            if len(sources) >= min_distinct_sources:
                alerts.append(
                    AMLAlert(
                        kind=AlertKind.FAN_IN,
                        severity=Severity.WARN,
                        primary_account=account_id,
                        related_accounts=tuple(sorted(sources)),
                        total_amount_vnd=sum(t.amount_vnd for t in bucket),
                        detail=(
                            f"received from {len(sources)} distinct sources in "
                            f"{window_seconds}s window (threshold {min_distinct_sources})"
                        ),
                        txn_ids=tuple(t.txn_id for t in bucket),
                    )
                )
                break
    return alerts


# ---------------------------------------------------------------------------
# Layering chain.


def detect_layering_chains(
    graph: TransactionGraph,
    *,
    min_depth: int = 3,
    hop_seconds: int = 1800,
    total_seconds: int = 86_400,
) -> list[AMLAlert]:
    """Find any directed path of ``min_depth`` hops where each step happens
    within ``hop_seconds`` of the previous, and the whole walk fits inside
    ``total_seconds``. Reports the *shortest qualifying* path per source.
    """
    if min_depth < 2:
        raise ValueError("min_depth must be >= 2")
    hop = timedelta(seconds=hop_seconds)
    total = timedelta(seconds=total_seconds)
    alerts: list[AMLAlert] = []
    seen_sources: set[str] = set()
    for source in sorted(graph.all_known_account_ids()):
        if source in seen_sources:
            continue
        # Iterative DFS with explicit stack so we can prune.
        stack: list[tuple[list[Transaction], set[str]]] = []
        for first in sorted(graph.out_edges(source), key=lambda t: t.occurred_at):
            stack.append(([first], {source, first.to_account}))
        while stack:
            path, visited = stack.pop()
            if len(path) >= min_depth:
                full_amount = path[0].amount_vnd
                alerts.append(
                    AMLAlert(
                        kind=AlertKind.LAYERING_CHAIN,
                        severity=Severity.CRIT,
                        primary_account=source,
                        related_accounts=tuple(t.to_account for t in path),
                        total_amount_vnd=full_amount,
                        detail=(
                            f"chain of length {len(path)}: "
                            + " → ".join([source] + [t.to_account for t in path])
                        ),
                        txn_ids=tuple(t.txn_id for t in path),
                    )
                )
                seen_sources.add(source)
                break
            last = path[-1]
            elapsed = last.occurred_at - path[0].occurred_at
            if elapsed > total:
                continue
            for nxt in graph.out_edges(last.to_account):
                if nxt.to_account in visited:
                    continue
                if not (last.occurred_at < nxt.occurred_at <= last.occurred_at + hop):
                    continue
                if (nxt.occurred_at - path[0].occurred_at) > total:
                    continue
                stack.append(([*path, nxt], visited | {nxt.to_account}))
    return alerts


# ---------------------------------------------------------------------------
# Round-trip.


def detect_round_trips(
    graph: TransactionGraph,
    *,
    max_depth: int = 5,
    window_seconds: int = 86_400,
) -> list[AMLAlert]:
    """Find cycles where money returns to its origin via ≥ 1 intermediary."""
    if max_depth < 2:
        raise ValueError("max_depth must be >= 2 (need at least one intermediary)")
    window = timedelta(seconds=window_seconds)
    alerts: list[AMLAlert] = []
    reported: set[str] = set()
    for source in sorted(graph.all_known_account_ids()):
        if source in reported:
            continue
        stack: list[tuple[list[Transaction], set[str]]] = []
        for first in sorted(graph.out_edges(source), key=lambda t: t.occurred_at):
            stack.append(([first], {first.to_account}))
        while stack:
            path, visited = stack.pop()
            last = path[-1]
            elapsed = last.occurred_at - path[0].occurred_at
            if elapsed > window:
                continue
            if len(path) > max_depth:
                continue
            for nxt in graph.out_edges(last.to_account):
                if not (last.occurred_at < nxt.occurred_at <= path[0].occurred_at + window):
                    continue
                if nxt.to_account == source and len(path) >= 1:
                    alerts.append(
                        AMLAlert(
                            kind=AlertKind.ROUND_TRIP,
                            severity=Severity.CRIT,
                            primary_account=source,
                            related_accounts=tuple(t.to_account for t in path),
                            total_amount_vnd=path[0].amount_vnd,
                            detail=(
                                f"cycle of length {len(path) + 1} "
                                + " → ".join([source] + [t.to_account for t in path] + [source])
                            ),
                            txn_ids=tuple(t.txn_id for t in [*path, nxt]),
                        )
                    )
                    reported.add(source)
                    stack.clear()
                    break
                if nxt.to_account not in visited:
                    stack.append(([*path, nxt], visited | {nxt.to_account}))
    return alerts


# ---------------------------------------------------------------------------
# Structured deposit.


def detect_structured_deposits(
    graph: TransactionGraph,
    *,
    threshold_vnd: int = 10_000_000,
    margin_vnd: int = 500_000,
    min_count: int = 3,
    min_distinct_sources: int = 2,
    window_seconds: int = 3600,
) -> list[AMLAlert]:
    """Per-recipient version of structuring: many just-under-threshold
    incoming transfers from multiple sources within a short window."""
    if margin_vnd <= 0 or margin_vnd >= threshold_vnd:
        raise ValueError("margin_vnd must be in (0, threshold_vnd)")
    if min_count < 2:
        raise ValueError("min_count must be >= 2")
    window = timedelta(seconds=window_seconds)
    alerts: list[AMLAlert] = []
    for account_id in sorted(graph.all_known_account_ids()):
        ins = sorted(
            (
                t
                for t in graph.in_edges(account_id)
                if threshold_vnd - margin_vnd < t.amount_vnd <= threshold_vnd
            ),
            key=lambda t: t.occurred_at,
        )
        if len(ins) < min_count:
            continue
        for i, anchor in enumerate(ins):
            cutoff = anchor.occurred_at + window
            bucket: list[Transaction] = []
            for t in ins[i:]:
                if t.occurred_at > cutoff:
                    break
                bucket.append(t)
            sources = {t.from_account for t in bucket}
            if len(bucket) >= min_count and len(sources) >= min_distinct_sources:
                alerts.append(
                    AMLAlert(
                        kind=AlertKind.STRUCTURED_DEPOSIT,
                        severity=Severity.WARN,
                        primary_account=account_id,
                        related_accounts=tuple(sorted(sources)),
                        total_amount_vnd=sum(t.amount_vnd for t in bucket),
                        detail=(
                            f"{len(bucket)} near-threshold deposits from "
                            f"{len(sources)} sources in {window_seconds}s window"
                        ),
                        txn_ids=tuple(t.txn_id for t in bucket),
                    )
                )
                break
    return alerts


__all__ = [
    "detect_fan_in",
    "detect_fan_out",
    "detect_layering_chains",
    "detect_round_trips",
    "detect_structured_deposits",
]
