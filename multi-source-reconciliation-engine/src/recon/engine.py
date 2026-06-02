"""Core reconciliation engine: fuzzy multi-key matching + discrepancy classification."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from recon.schema import DiscrepancyType, MatchResult, ReconReport, Transaction

_ROUNDING_THRESHOLD = 0.015  # ≤ 1.5 cents treated as rounding


def _normalise_ref(ref: str) -> str:
    """Strip common prefixes/suffixes and normalise case."""
    return ref.strip().upper().lstrip("0")


def _ref_similarity(a: str, b: str) -> float:
    """Jaro–Winkler-style similarity in pure stdlib (fallback: exact after normalise)."""
    na, nb = _normalise_ref(a), _normalise_ref(b)
    if na == nb:
        return 1.0
    # simple edit-distance based score
    la, lb = len(na), len(nb)
    if la == 0 or lb == 0:
        return 0.0
    # common prefix bonus (Winkler)
    prefix = 0
    for ca, cb in zip(na, nb, strict=False):
        if ca == cb:
            prefix += 1
        else:
            break
    # Jaro
    match_window = max(la, lb) // 2 - 1
    if match_window < 0:
        match_window = 0
    a_matches = [False] * la
    b_matches = [False] * lb
    matches = 0
    for i, ca in enumerate(na):
        lo = max(0, i - match_window)
        hi = min(lb, i + match_window + 1)
        for j in range(lo, hi):
            if not b_matches[j] and ca == nb[j]:
                a_matches[i] = True
                b_matches[j] = True
                matches += 1
                break
    if matches == 0:
        return 0.0
    transpositions = 0
    k = 0
    for i in range(la):
        if a_matches[i]:
            while not b_matches[k]:
                k += 1
            if na[i] != nb[k]:
                transpositions += 1
            k += 1
    jaro = (matches / la + matches / lb + (matches - transpositions / 2) / matches) / 3
    # Winkler scaling
    p = 0.1
    return jaro + min(prefix, 4) * p * (1 - jaro)


def _amount_confidence(amounts: list[float]) -> tuple[float, float]:
    """Return (delta, confidence) for a set of amounts from different sources."""
    if not amounts:
        return 0.0, 0.0
    mn, mx = min(amounts), max(amounts)
    delta = abs(mx - mn)
    if delta == 0.0:
        return 0.0, 1.0
    if delta <= _ROUNDING_THRESHOLD:
        return delta, 0.9
    avg = sum(amounts) / len(amounts)
    rel = delta / (abs(avg) + 1e-9)
    return delta, max(0.0, 1.0 - rel)


def _date_confidence(dates: list[date]) -> float:
    if len(dates) <= 1:
        return 1.0
    spread = (max(dates) - min(dates)).days
    if spread == 0:
        return 1.0
    if spread <= 1:
        return 0.95
    if spread <= 3:
        return 0.8
    return max(0.0, 1.0 - spread / 10)


def _classify(
    delta: float,
    amount_conf: float,
    date_conf: float,
    n_sources: int,
    expected_sources: int,
) -> DiscrepancyType:
    missing = n_sources < expected_sources
    amount_mismatch = delta > _ROUNDING_THRESHOLD
    rounding = 0 < delta <= _ROUNDING_THRESHOLD
    timing = date_conf < 0.95

    issues = sum([missing, amount_mismatch, timing])
    if issues == 0 and not rounding:
        return DiscrepancyType.MATCHED
    if issues >= 2:
        return DiscrepancyType.MULTI
    if missing and not amount_mismatch:
        return DiscrepancyType.MISSING
    if amount_mismatch:
        return DiscrepancyType.AMOUNT_MISMATCH
    if rounding:
        return DiscrepancyType.ROUNDING
    return DiscrepancyType.TIMING


class ReconciliationEngine:
    """Match transactions from multiple sources by fuzzy ref + amount + date."""

    def __init__(
        self,
        ref_threshold: float = 0.85,
        date_window_days: int = 3,
    ) -> None:
        self.ref_threshold = ref_threshold
        self.date_window_days = date_window_days

    def reconcile(
        self,
        sources: dict[str, list[Transaction]],
    ) -> ReconReport:
        """Run full reconciliation and return a ``ReconReport``."""
        source_names = list(sources.keys())
        n_expected = len(source_names)

        # Index all transactions by normalised ref
        groups: dict[str, list[Transaction]] = defaultdict(list)
        for txns in sources.values():
            for txn in txns:
                groups[_normalise_ref(txn.ref)].append(txn)

        # Merge groups with high ref similarity (fuzzy grouping)
        merged = _fuzzy_merge_groups(dict(groups), self.ref_threshold)

        results: list[MatchResult] = []
        for ref_key, txns in sorted(merged.items()):
            amounts = [t.amount for t in txns]
            dates = [t.txn_date for t in txns]
            srcs = list({t.source for t in txns})
            delta, a_conf = _amount_confidence(amounts)
            d_conf = _date_confidence(dates)
            dtype = _classify(delta, a_conf, d_conf, len(srcs), n_expected)
            confidence = (a_conf + d_conf) / 2
            notes = _build_notes(srcs, source_names, delta, dates)
            results.append(
                MatchResult(
                    ref=ref_key,
                    status=dtype,
                    sources_present=sorted(srcs),
                    transactions=txns,
                    amount_delta=delta,
                    confidence=round(confidence, 4),
                    notes=notes,
                )
            )

        matched = sum(1 for r in results if r.status == DiscrepancyType.MATCHED)
        total = sum(len(v) for v in sources.values())
        return ReconReport(
            run_date=date.today(),
            sources=source_names,
            total_records=total,
            matched=matched,
            discrepancies=len(results) - matched,
            results=results,
        )


def _fuzzy_merge_groups(
    groups: dict[str, list[Transaction]],
    threshold: float,
) -> dict[str, list[Transaction]]:
    """Merge groups whose normalised refs are above similarity threshold."""
    keys = list(groups.keys())
    parent: dict[str, str] = {k: k for k in keys}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            if _ref_similarity(a, b) >= threshold:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[rb] = ra

    merged: dict[str, list[Transaction]] = defaultdict(list)
    for k, txns in groups.items():
        merged[find(k)].extend(txns)
    return dict(merged)


def _build_notes(
    present: list[str],
    expected: list[str],
    delta: float,
    dates: list[date],
) -> str:
    parts: list[str] = []
    missing = [s for s in expected if s not in present]
    if missing:
        parts.append(f"missing from: {', '.join(missing)}")
    if delta > 0:
        parts.append(f"amount delta: {delta:.4f}")
    if len(dates) > 1:
        spread = (max(dates) - min(dates)).days
        if spread > 0:
            parts.append(f"date spread: {spread}d")
    return "; ".join(parts)


def reconcile(
    sources: dict[str, list[Transaction]],
    ref_threshold: float = 0.85,
    date_window_days: int = 3,
) -> ReconReport:
    """Functional entry-point: reconcile sources and return report."""
    return ReconciliationEngine(
        ref_threshold=ref_threshold,
        date_window_days=date_window_days,
    ).reconcile(sources)
