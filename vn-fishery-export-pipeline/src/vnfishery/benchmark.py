"""Benchmark FOB prices and anti-dumping watchlist.

Anti-dumping (chống bán phá giá) is a real recurring issue for VN
seafood exporters — the US DOC has imposed pangasius and shrimp duties
for years, and the EU periodically threatens IUU (illegal, unreported,
unregulated) action. The benchmark prices in this module are
**illustrative** (rough mid-2026 spot-market values from VASEP's
public bulletins) — not official reference prices.

When an exporter's quoted FOB price falls **materially below** the
benchmark for the same species/market/grade combination, we flag it
as a dumping risk for downstream investigation.
"""

from __future__ import annotations

from vnfishery.schema import Grade, Market, Species

# Reference FOB prices, USD per kg, by (species, market, grade).
# Numbers are deliberately conservative round figures — production use
# should plug in VASEP weekly bulletins or the ITC trade database.
_BENCHMARK: dict[tuple[Species, Market, Grade], float] = {
    # Pangasius (cá tra) — US is the big buyer, EU pays slightly less.
    (Species.PANGASIUS, Market.US, Grade.A): 3.20,
    (Species.PANGASIUS, Market.US, Grade.B): 2.60,
    (Species.PANGASIUS, Market.EU, Grade.A): 2.80,
    (Species.PANGASIUS, Market.EU, Grade.B): 2.30,
    (Species.PANGASIUS, Market.CN, Grade.A): 2.20,
    (Species.PANGASIUS, Market.CN, Grade.B): 1.80,
    # White shrimp (tôm thẻ chân trắng) — Japan is premium buyer.
    (Species.WHITE_SHRIMP, Market.US, Grade.A): 8.50,
    (Species.WHITE_SHRIMP, Market.US, Grade.B): 7.00,
    (Species.WHITE_SHRIMP, Market.JP, Grade.A): 11.00,
    (Species.WHITE_SHRIMP, Market.JP, Grade.B): 9.20,
    (Species.WHITE_SHRIMP, Market.EU, Grade.A): 9.00,
    (Species.WHITE_SHRIMP, Market.KR, Grade.A): 8.80,
    # Black tiger (tôm sú) — premium product, Japan-dominated.
    (Species.BLACK_TIGER, Market.JP, Grade.A): 13.50,
    (Species.BLACK_TIGER, Market.US, Grade.A): 11.00,
    (Species.BLACK_TIGER, Market.EU, Grade.A): 12.00,
    # Squid (mực) — Korea and China.
    (Species.SQUID, Market.KR, Grade.A): 5.50,
    (Species.SQUID, Market.CN, Grade.A): 4.80,
    (Species.SQUID, Market.JP, Grade.A): 6.20,
    # Tuna (cá ngừ) — sashimi-grade in JP, fillet in US.
    (Species.TUNA, Market.JP, Grade.A): 14.00,
    (Species.TUNA, Market.US, Grade.A): 7.50,
    (Species.TUNA, Market.EU, Grade.A): 8.00,
}

# Dumping threshold: 25% below benchmark triggers a flag. Industry
# investigators typically use a sliding scale; we keep it simple.
DUMPING_THRESHOLD_PCT = 0.25


def benchmark_usd_cents_per_kg(species: Species, market: Market, grade: Grade) -> int | None:
    """Look up benchmark FOB price for a (species, market, grade) cell.

    Returns ``None`` if no benchmark is available — the caller should
    treat unknown cells as "cannot judge" rather than "ok".
    """
    val = _BENCHMARK.get((species, market, grade))
    if val is None:
        return None
    return int(round(val * 100))  # USD → cents


def is_dumping_risk(
    species: Species,
    market: Market,
    grade: Grade,
    quoted_price_usd_cents_per_kg: int,
    threshold_pct: float = DUMPING_THRESHOLD_PCT,
) -> bool:
    """Flag a quoted FOB price as suspicious if it's significantly
    below the benchmark.

    Returns ``False`` when no benchmark exists (we don't flag the
    unknown — that's the caller's call).
    """
    if not 0.0 < threshold_pct < 1.0:
        raise ValueError("threshold_pct must be in (0, 1)")
    bench = benchmark_usd_cents_per_kg(species, market, grade)
    if bench is None:
        return False
    floor = int(round(bench * (1.0 - threshold_pct)))
    return quoted_price_usd_cents_per_kg < floor


__all__ = [
    "DUMPING_THRESHOLD_PCT",
    "benchmark_usd_cents_per_kg",
    "is_dumping_risk",
]
