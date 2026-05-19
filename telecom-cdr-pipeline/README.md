# telecom-cdr-pipeline

End-to-end **Vietnamese telecom CDR (Call Detail Record) pipeline** —
rate raw CDRs against the published 2024-2026 tariff, aggregate into
per-subscriber monthly bills (10% VAT per the VN VAT Law), and surface
three classic VN-context fraud signals: premium-rate spikes,
foreign-roaming anomalies, SIM-swap.

Pure Python 3.10+, zero runtime dependencies (stdlib only), 153 tests
including Hypothesis property tests, `mypy --strict` clean.

## What's in the box

| Module                  | Purpose                                              |
| ----------------------- | ---------------------------------------------------- |
| `cdrpipe.schema`        | `CDR`, `RatedCDR`, `MonthlyBill`, `Carrier`, `CDRKind`, `PlanKind` |
| `cdrpipe.carriers`      | 5 VN carriers + prefix tables (Decision 2730/QĐ-BTTTT 2018) |
| `cdrpipe.rating`        | Peak/off-peak voice, on-net/off-net, premium, roaming, 10% VAT |
| `cdrpipe.billing`       | Monthly bill aggregation per subscriber              |
| `cdrpipe.fraud`         | Premium-rate spike, foreign-roaming, SIM-swap        |
| `cdrpipe.simulator`     | Deterministic seeded CDR stream generator            |
| `cdrpipe.io_jsonl`      | JSONL codec for every record type                    |
| `cdrpipe.cli`           | `info | simulate | rate | bill | fraud | summary`   |

## Quick start

```bash
# Simulate one month of 100 subscribers
python -m cdrpipe.cli simulate --subscribers 100 --days 30 --seed 11 \
  --output cdrs.jsonl

# Apply tariff
python -m cdrpipe.cli rate --input cdrs.jsonl --output rated.jsonl --show 5

# Roll up into monthly bills
python -m cdrpipe.cli bill --input cdrs.jsonl --output bills.jsonl --show 5

# Run all three fraud detectors (exits 2 if anything fires)
python -m cdrpipe.cli fraud --input cdrs.jsonl

# JSON summary of the whole run
python -m cdrpipe.cli summary --input cdrs.jsonl
```

## VN carrier directory

Five operators allocated to fixed 3-digit MSISDN prefixes:

| Carrier        | Prefixes                                     | Share |
| -------------- | -------------------------------------------- | ----- |
| Viettel Mobile | `086 096 097 098 032-039`                    | 53%   |
| VinaPhone      | `081-085 088 091 094`                        | 24%   |
| MobiFone       | `070 076-079 089 090 093`                    | 17%   |
| Vietnamobile   | `056 058 092`                                | 3%    |
| Reddi          | `055 059`                                    | 1%    |

`carrier_for("+84961234567")`, `carrier_for("0961234567")` and
`carrier_for("961234567")` all return `Carrier.VIETTEL` — the
`normalise_msisdn` helper handles all three forms.

## Tariff & VAT

Defaults match the published 2024-2026 retail mobile tariff:

| Resource           | On-net peak | Off-net peak | Off-peak |
| ------------------ | ----------- | ------------ | -------- |
| Voice (VND/min)    | 1,580       | 1,780        | -200 each |
| SMS (VND/msg)      | 290         | 390          | flat     |
| Data (VND/MB)      | 50          | 50           | flat     |
| Premium voice      | 8,000       | 8,000        | flat     |
| Roaming voice      | 8,000       | 8,000        | flat     |
| Roaming SMS        | 2,500       | 2,500        | flat     |
| Roaming data       | 200/MB      | 200/MB       | flat     |

Peak window is 06:00–22:00 VN local time. Calls shorter than 6 seconds
are free (Block-6 rounding); 6-60s = 1 minute; beyond 60s rounds up to
the next minute. VAT is exactly 10% per Article 8 of the VN VAT Law
2008 (latest amendment 2024).

All money is **integer VND** — no `Decimal`, no float drift.

## Fraud detection

* **Premium-rate spike** — flags a subscriber whose 1900XXX premium
  voice usage exceeds 30 minutes in a single day (typical legitimate
  use < 2 min/day).
* **Foreign-roaming anomaly** — flags any roaming charge above
  100,000 VND. Configurable threshold via `--min-roaming-amount`.
* **SIM-swap signal** — flags subscribers whose last 24h of calls
  shows a peer set with Jaccard similarity < 0.10 against the prior
  30-day baseline (heuristic for stolen-SIM number reassignment).

## Quality gate

```
ruff check src tests                  # zero issues
ruff format --check src tests         # zero diffs
mypy --strict src                     # 0 errors in 9 files
pytest                                # 153 tests, all green
```

Property tests exercise rating-amount conservation, VAT 10% identity,
JSONL round-trip, and MSISDN normalisation idempotency via Hypothesis.

## License

MIT
