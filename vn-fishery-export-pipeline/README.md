# vn-fishery-export-pipeline

VN seafood export records — species/market/grade catalog, FOB pricing
aggregation, anti-dumping watchlist.

## What it does

Vietnam exports ~$10 B of seafood annually (VASEP), with five flagship
species (pangasius/cá tra, white shrimp, black tiger shrimp, squid,
tuna) into five anchor markets (US, EU, Japan, China, Korea). This
pipeline normalises shipment-level records, rolls them up by axis, and
flags FOB prices that fall under a configurable dumping threshold —
useful for upstream alerting when a trade investigation (DOC/EU IUU)
is looming.

* **Schema** — `ExportRecord` (frozen-slots) with species/market/grade/
  form enums, weight + USD-cents FOB price, derived
  `fob_value_usd_cents`.
* **Benchmark** — illustrative reference FOB prices keyed by
  `(species, market, grade)` plus `is_dumping_risk` predicate.
* **Aggregate** — group totals by species, market, species×market, or
  exporter tax code.

## Quick start

```bash
pip install vn-fishery-export-pipeline
vnfishery info
vnfishery benchmark --species pangasius --market US --grade A
vnfishery simulate --n 200 --seed 0 --output raw.jsonl
vnfishery aggregate --input raw.jsonl --output agg.jsonl
vnfishery dumping-watch --input raw.jsonl --output flagged.jsonl
```

## Library

```python
from vnfishery import (
    ExportRecord, Species, Market, Grade, Form,
    is_dumping_risk, aggregate_by_species_market,
)
from datetime import date

r = ExportRecord(
    shipment_id="S-001",
    exporter_tax_code="0312345678",
    species=Species.PANGASIUS,
    market=Market.US,
    grade=Grade.A,
    form=Form.FILLET,
    weight_kg=10_000,
    fob_price_usd_cents_per_kg=150,  # $1.50/kg — well below US benchmark
    shipped_on=date(2026, 3, 15),
)
print(is_dumping_risk(r.species, r.market, r.grade, r.fob_price_usd_cents_per_kg))
# → True
```

## Caveats

* Benchmark prices are **illustrative** — production work should ingest
  VASEP weekly bulletins or ITC trade-database snapshots.
* The 25 % dumping threshold is a heuristic; real investigators use a
  sliding scale tied to constructed value and surrogate-country
  margins (per US DOC methodology).
* The `OTHER` species/market enums are catch-alls; tighten them when
  you bind to a real upstream feed.

## License

MIT.
