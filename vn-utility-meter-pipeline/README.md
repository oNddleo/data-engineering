# vn-utility-meter-pipeline

End-to-end **Vietnamese electricity meter pipeline** as administered
by **Tập đoàn Điện lực Việt Nam (EVN)** — the 5-corporation directory
(PA / PB / PC / PD / PE), 6-tier progressive household tariff per
Decision 2699/QĐ-BCT (the *bậc thang* schedule), flat tariffs for
business / admin / production / agriculture categories, monthly
billing with 10% VAT per Decree 209/2013/NĐ-CP, annual roll-up, and
three meter-reading anomaly detectors (zero usage, sudden drop,
unrealistic spike).

Pure Python 3.10+, zero runtime dependencies (stdlib only), 134 tests
including Hypothesis property tests, `mypy --strict` clean.

## What's in the box

| Module             | Purpose                                              |
| ------------------ | ---------------------------------------------------- |
| `evn.schema`       | `MeterReading`, `ElectricityBill`, `TierUsage`, `AnomalyFinding` |
| `evn.tariff`       | `HouseholdTariff` (6-tier) + `FlatTariff` schedules with date-effective lookup |
| `evn.customer`     | 5-unit EVN regional directory + 13-char code validator |
| `evn.billing`      | `compute_bill(reading)` — progressive tier slicing + VAT |
| `evn.aggregator`   | Annual per-customer rollup                           |
| `evn.anomaly`      | Zero usage / sudden drop / unrealistic spike detectors |
| `evn.simulator`    | Seeded household + business + production stream     |
| `evn.io_jsonl`     | JSONL codec for every record type                    |
| `evn.cli`          | `info | units | tariff | simulate | bill | summary | anomaly` |

## Quick start

```bash
# List the 5 EVN provincial units
python -m evn.cli units

# Inspect the active tariff schedule
python -m evn.cli tariff --date 2025-06-15

# Simulate a year of monthly meter readings
python -m evn.cli simulate --customers 100 --months 12 --seed 11 \
  --output readings.jsonl

# Compute bills + annual summaries
python -m evn.cli bill --input readings.jsonl --output bills.jsonl --show 5
python -m evn.cli summary --input readings.jsonl --show 5

# Detect tampering / spike anomalies (exits 2 on findings)
python -m evn.cli anomaly --input readings.jsonl --show 5
```

```python
from datetime import date
from evn import compute_bill, MeterReading, CustomerCategory

reading = MeterReading(
    customer_code="PE12345678901",
    category=CustomerCategory.HOUSEHOLD,
    period_start=date(2025, 6, 1),
    period_end=date(2025, 6, 30),
    kwh_used=350,
)
bill = compute_bill(reading)
print(f"Total: {bill.total_amount_vnd:,} VND")
# Tiered breakdown:
for t in bill.tier_breakdown:
    print(f"  Tier {t.tier_index}: {t.kwh} kWh × {t.rate_vnd_per_kwh} = {t.amount_vnd:,} VND")
```

## EVN provincial unit directory

| Prefix | Corporation       | Coverage                                |
| ------ | ----------------- | --------------------------------------- |
| PA     | EVNHANOI          | Hà Nội                                  |
| PB     | EVNNPC            | 27 northern provinces (excl. Hà Nội)    |
| PC     | EVNCPC            | 13 central + Tây Nguyên provinces       |
| PD     | EVNSPC            | 21 southern provinces (excl. HCMC)      |
| PE     | EVNHCMC           | TP Hồ Chí Minh                          |

Customer codes are 13 characters: a 2-letter prefix + 11 digits.

## Tariff schedule (Decision 2699/QĐ-BCT, effective 2024-10-11)

Household 6-tier progressive (*bậc thang*):

| Tier | Range (kWh)   | VND/kWh |
| ---- | ------------- | ------- |
| 1    | 0 – 50        | 1 893   |
| 2    | 51 – 100      | 1 956   |
| 3    | 101 – 200     | 2 271   |
| 4    | 201 – 300     | 2 860   |
| 5    | 301 – 400     | 3 197   |
| 6    | 401 +         | 3 302   |

Flat category rates (same decision):

| Category     | VND/kWh |
| ------------ | ------- |
| BUSINESS     | 2 752   |
| ADMIN_PUBLIC | 2 005   |
| PRODUCTION   | 2 159   |
| AGRICULTURE  | 1 644   |

VAT is 10% per Decree 209/2013/NĐ-CP — electricity stayed at 10%
through the COVID-era 8% reduction.

`tariff_for_date(d)` resolves to the schedule effective on `d`; we
also bundle the 2023-11-09 schedule (Decision 1416/QĐ-EVN) for
historical bills.

## Anomaly detection

* **Zero usage** — a 0-kWh month after a non-zero trailing window;
  true vacancies (zero throughout the trailing window) are not flagged.
* **Sudden drop** — current month dropped > 80% (configurable) below
  the trailing 3-month average. Strong meter-bypass signal.
* **Unrealistic spike** — current month spiked > 5× (configurable)
  the trailing 3-month average. Indicates billing-system error.

All three need ≥ 3 prior readings per customer. Outputs are
sorted by severity (largest drop / largest spike first).

## Quality gate

```
ruff check src tests          # 0 issues
ruff format --check src tests # 0 diffs
mypy --strict src             # 10 source files clean
pytest                        # 134 tests, all green
```

## License

MIT
