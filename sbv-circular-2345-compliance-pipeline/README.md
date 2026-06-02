# sbv-circular-2345-compliance-pipeline

Audit-trail pipeline cho mọi giao dịch chịu **Quyết định 2345/QĐ-NHNN**
(xác thực sinh trắc học) — hash-chained append-only ledger,
daily Merkle seal, 5-year retention enforcement, regulator-format
CSV export.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## How this differs from real-time monitoring

This project is the **compliance / audit-trail** half of the
QĐ 2345 stack. It's complementary to a real-time fraud-monitoring
system: where the monitor raises alerts as transactions flow past
in seconds, the compliance pipeline produces the immutable record
that SBV regulators read months later.

| Concern                          | Real-time monitor       | This audit pipeline      |
| -------------------------------- | ----------------------- | ------------------------ |
| Latency                          | < 1s per txn            | Batch end-of-day OK      |
| Output                           | Alerts → PagerDuty/Slack | Sealed records → ledger  |
| Mutability                       | Stateful, evolves       | Append-only, immutable   |
| Audience                         | Fraud ops               | SBV regulator + auditors |
| Retention                        | Hot for 30–90 days      | **≥ 5 years** (Điều 7)   |

## What it does

1. **Ingest** a `TransactionEvent` stream (Kafka, core-banking
   export, NAPAS feed — JSONL on disk for tests).
2. **Classify** each txn against four Decision 2345 triggers
   (single >10M, cumulative >20M/day, high-risk beneficiary,
   cross-border). Txns that fire **zero** triggers don't enter the
   audit ledger.
3. **Seal** each surviving event into a hash-chained
   `SealedAuditRecord` with sequence number, prev-hash, record-hash,
   and a canonical wall-clock seal time.
4. **Verify** chain integrity on load — any tamper (edit-in-place,
   reorder, fake-out-the-hash) is caught.
5. **Daily Merkle root** — Bitcoin-style binary Merkle over each
   day's record hashes. This is what banks ship in monthly
   compliance dossiers.
6. **Retention status + regulator CSV** — track which records are
   ACTIVE vs ARCHIVE_ELIGIBLE; export the canonical CSV columns SBV
   expects.

## The four Decision 2345 triggers

| Kind                          | Trigger when                                        | Legal basis           |
| ----------------------------- | --------------------------------------------------- | --------------------- |
| `SINGLE_TXN_OVER_10M`         | `amount_vnd > 10_000_000`                           | QĐ 2345 Điều 1.1      |
| `DAILY_CUMULATIVE_OVER_20M`   | `amount ≤ 10M` AND `daily_total_after > 20_000_000` | QĐ 2345 Điều 1.2      |
| `HIGH_RISK_BENEFICIARY`       | beneficiary in caller-supplied blacklist            | Thông tư 35/2013 AML  |
| `INTERNATIONAL_TRANSFER`      | `cross_border == True`                              | Pháp lệnh Ngoại hối   |

The single / cumulative kinds are **mutually exclusive by
construction** — a 30M-VND txn fires SINGLE only; the cumulative
branch is gated on `amount ≤ 10M`. The non-value triggers stack
independently on the value ones.

## Hash chain + Merkle seal

Each record's `record_hash` is computed as:

```
SHA-256(prev_hash || sequence_number_be8 || sealed_at_iso || canonical_json(event))
```

Where `canonical_json` is the event with keys sorted, no
whitespace, UTF-8 encoded. The first record's `prev_hash` is
`"0" * 64` (genesis).

`AuditLedger.verify()` walks the chain end-to-end, recomputing each
record's hash and asserting it matches the stored one. The
persistence layer (`io_jsonl.load_ledger`) calls `verify()` on
every load, so on-disk tampering of the JSONL file is caught at
ingest time — see `test_load_ledger_detects_on_disk_tamper`.

Daily seal:

```
DailySeal.merkle_root = merkle_root([rec.record_hash for rec in day_records])
```

Bitcoin-convention odd-leaf duplication. Empty day → `"0" * 64`.

## Components

| Module                | Role                                                                |
| --------------------- | ------------------------------------------------------------------- |
| `sbv2345.schema`      | `TransactionEvent`, `AuditEvent`, `TriggerKind`, enums              |
| `sbv2345.triggers`    | `Classifier` (per-account daily-total state, 4-trigger logic)       |
| `sbv2345.merkle`      | `merkle_root`, `hash_pair`, `EMPTY_ROOT`                            |
| `sbv2345.ledger`      | `AuditLedger`, `SealedAuditRecord`, `DailySeal`, `TamperDetected`   |
| `sbv2345.retention`   | 5-year `retention_cutoff`, `status`, `summarise`, `archive_candidates` |
| `sbv2345.reports`     | `regulator_csv`, `summarise` (by trigger / channel / auth_method)   |
| `sbv2345.io_jsonl`    | round-trippable codec + tamper-checking `load_ledger`               |
| `sbv2345.simulator`   | seeded synthetic txns covering every trigger kind                   |
| `sbv2345.cli`         | `sbv2345 info | simulate | ingest | verify | seal-day | report | retention` |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
sbv2345 info

# 1) Generate a synthetic transaction stream covering every trigger.
sbv2345 simulate \
  --small 50 --large 5 --cumulative 2 --cross-border 2 \
  --high-risk BAD-ACCOUNT-001 \
  --seed 42 \
  --output txns.jsonl

# 2) Classify + seal into the audit ledger.
sbv2345 ingest \
  --input txns.jsonl \
  --high-risk BAD-ACCOUNT-001 \
  --output ledger.jsonl

# 3) Verify the chain.
sbv2345 verify --ledger ledger.jsonl
# → "ledger chain OK"

# 4) Compute the daily Merkle root.
sbv2345 seal-day --ledger ledger.jsonl --day 2026-05-14
# → { day, record_count, merkle_root, sealed_at }

# 5) Export the regulator-format CSV.
sbv2345 report --ledger ledger.jsonl --format csv > regulator-2026-05.csv

# 6) Or a JSON summary by trigger / channel / auth method.
sbv2345 report --ledger ledger.jsonl --format json

# 7) Retention summary.
sbv2345 retention --ledger ledger.jsonl --today 2031-06-01
```

End-to-end on a 10-txn synthetic stream (3 large + 2 cumulative
triples + 1 cross-border):

```
$ sbv2345 ingest --input txns.jsonl --output ledger.jsonl
sealed 6 audit-worthy events to ledger.jsonl (6 ledger rows)

$ sbv2345 verify --ledger ledger.jsonl
ledger chain OK

$ sbv2345 seal-day --ledger ledger.jsonl --day 2026-05-14
{ "day": "2026-05-14", "record_count": 6,
  "merkle_root": "e69eb9e2a018227c4b243c0bd740f3ee...", ... }

$ sbv2345 report --ledger ledger.jsonl --format json
{ "total": 6,
  "by_trigger": {"SINGLE_TXN_OVER_10M": 3, "DAILY_CUMULATIVE_OVER_20M": 2,
                 "INTERNATIONAL_TRANSFER": 1},
  "biometric_verified_count": 3, ... }
```

Tamper test:

```
$ sed -i.bak 's/MOBILE_APP/INTERNET_BANKING/' ledger.jsonl
$ sbv2345 verify --ledger ledger.jsonl
TAMPER DETECTED at sequence 1: record_hash does not match computed hash
```

## Library

```python
from sbv2345 import (
    AuditLedger, Classifier, generate, load_ledger, dump_ledger, regulator_csv,
)
from datetime import datetime
from sbv2345.schema import VN_TZ

now = datetime.now(tz=VN_TZ)
classifier = Classifier(high_risk_accounts={"BAD-001"})
ledger = AuditLedger()

for txn in generate(seed=42):
    event = classifier.classify(txn)
    if event is not None:
        ledger.append(event, sealed_at=now)

ledger.verify()
seal = ledger.seal_day(now.date(), sealed_at=now)
print(f"Day {seal.day}: {seal.record_count} records, root={seal.merkle_root[:16]}…")

with open("regulator.csv", "w") as f:
    f.write(regulator_csv(ledger.records()))
```

## Retention

5-year retention is **calendar-based**: `retention_cutoff(today) =
today − 5 years`, with Feb 29 falling back to Feb 28 in non-leap
target years. A record's `sealed_at.date() < cutoff` makes it
`ARCHIVE_ELIGIBLE`; everything else is `ACTIVE`.

`archive_candidates(ledger, today)` returns the slice that can be
moved to cold / immutable storage. The pipeline never **deletes**
records — that's deliberately out of scope, because legal-hold
overrides typically push retention beyond 5 years.

## Quality

```bash
make test       # 104 tests, 5 Hypothesis properties
make type       # mypy --strict
make lint
```

- **104 tests** including 5 Hypothesis properties:
  - TransactionEvent JSONL round-trips for any positive VND amount
  - `AuditLedger.verify()` never raises on a freshly-built clean chain
  - Merkle root is deterministic for any leaf-count
  - Non-empty Merkle root is always 64-char hex
  - Dump → load ledger round-trips for any chain length
- mypy `--strict` clean over 10 source files; ruff + ruff-format
  clean.
- Multi-stage slim Docker image, non-root `sbv` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
