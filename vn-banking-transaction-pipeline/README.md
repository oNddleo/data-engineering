# vn-banking-transaction-pipeline

End-to-end **Vietnamese commercial banking pipeline** —  18-bank
directory with NAPAS BIN codes, VietQR codec (EMV TLV + CRC-16/CCITT),
NAPAS-247 / Citad routing, daily per-account summaries, and AML
signals (CTR, structuring, high-velocity) per VN regulations.

Pure Python 3.10+, zero runtime dependencies (stdlib only), 117 tests
including Hypothesis property tests, `mypy --strict` clean.

## What's in the box

| Module                 | Purpose                                          |
| ---------------------- | ------------------------------------------------ |
| `vnbank.schema`        | `Bank`, `Account`, `Transaction`, `TxnKind`, `TxnStatus`, `DailySummary` |
| `vnbank.banks`         | 18 VN commercial banks + BIN/abbreviation lookups |
| `vnbank.vietqr`        | VietQR build / parse with CRC-16/CCITT validation |
| `vnbank.routing`       | NAPAS-247 vs Citad rail selection + fee schedule  |
| `vnbank.summary`       | Daily per-account rollup                          |
| `vnbank.aml`           | CTR, structuring, high-velocity detectors         |
| `vnbank.simulator`     | Deterministic seeded transaction stream           |
| `vnbank.io_jsonl`      | JSONL codec for every record type                 |
| `vnbank.cli`           | `info | banks | qr | simulate | summary | aml | route` |

## Quick start

```bash
# List the bundled bank directory
python -m vnbank.cli banks

# Build a VietQR payload (paste into any banking app to pay)
python -m vnbank.cli qr --bank-bin 970436 --account-number 1234567890 \
  --amount 100000 --purpose "Test"

# Parse a VietQR payload back
python -m vnbank.cli qr --parse "00020101021238..."

# Compute the routing decision for a 50M VND inter-bank transfer
python -m vnbank.cli route --sender-bin 970436 --receiver-bin 970418 \
  --amount 50000000

# Simulate a month of 100 accounts and detect AML patterns
python -m vnbank.cli simulate --accounts 100 --days 30 --seed 11 \
  --output txns.jsonl
python -m vnbank.cli summary --input txns.jsonl --show 5
python -m vnbank.cli aml --input txns.jsonl --show 5
```

## VN bank directory (top 18 by deposit market share)

| BIN    | Abbr     | Name (EN)                                            | Share |
| ------ | -------- | ---------------------------------------------------- | ----- |
| 970418 | BIDV     | Bank for Investment and Development of Vietnam       | 14.5% |
| 970405 | AGRIBANK | Vietnam Bank for Agriculture and Rural Development   | 13.8% |
| 970436 | VCB      | Vietcombank                                          | 11.4% |
| 970415 | VTB      | VietinBank                                           | 10.6% |
| 970422 | MB       | Military Commercial JSB                              |  6.3% |
| 970407 | TCB      | Techcombank                                          |  5.8% |
| 970432 | VPB      | VPBank                                               |  5.1% |
| 970416 | ACB      | Asia Commercial Bank                                 |  4.3% |
| 970403 | STB      | Sacombank                                            |  3.5% |
| 970443 | SHB      | SHB                                                  |  3.2% |
| 970423 | TPB      | TPBank                                               |  2.7% |
| 970437 | HDB      | HDBank                                               |  2.3% |
| 970441 | VIB      | VIB                                                  |  2.1% |
| 970426 | MSB      | Maritime Bank                                        |  1.9% |
| 970448 | OCB      | Orient Commercial Bank                               |  1.6% |
| 970440 | SEAB     | SeABank                                              |  1.5% |
| 970431 | EIB      | Eximbank                                             |  1.3% |
| 970454 | VCCB     | Viet Capital Bank                                    |  0.9% |

Total bundled share: ~92% of VN retail-banking deposits.

## VietQR

Implements the EMV-spec TLV format used by NAPAS for the national QR
payment standard (live since March 2022). Supports both static QRs
(payer enters amount) and dynamic QRs (amount fixed). Round-trips
byte-exact with full CRC-16/CCITT-FALSE verification.

```python
from vnbank import build_vietqr, parse_vietqr

qr = build_vietqr(
    bank_bin="970436", account_number="1234567890",
    amount_vnd=100_000, purpose="Order 42",
)
parsed = parse_vietqr(qr)
assert parsed.bank_bin == "970436"
assert parsed.amount_vnd == 100_000
```

## NAPAS routing

* **Intra-bank** (same bank both sides) → in-house, no fee.
* **Interbank ≤ 500M VND** → NAPAS-247 (24/7 instant retail rail). Cap
  raised from 100M → 500M VND on 2024-07-01 per SBV Decision
  1085/QĐ-NHNN.
* **Interbank > 500M VND** → Citad (SBV's RTGS, batch clearing).

Fees follow the 2025 market-blended schedule (free under 1M, flat
5,000 VND tier, capped 50,000 for NAPAS; 0.02% capped at 1,000,000 VND
for Citad).

## AML signals

* **CTR** (Currency Transaction Report) per Decree 87/2017/NĐ-CP +
  Circular 09/2017/TT-NHNN — any daily cash flow ≥ **300,000,000 VND**
  must be reported to the SBV AML Department within one business day.
* **Structuring** — splitting cash deposits into multiple sub-threshold
  pieces to evade CTR (≥ 3 deposits in one day, all < 300M, summing
  to ≥ 300M).
* **High-velocity** — ≥ 50 outbound debits within a 1-hour rolling
  window (money-mule pattern).

```python
from vnbank import find_ctr, find_structuring, find_high_velocity, load_txns

txns = load_txns(open("txns.jsonl").read())
for f in find_ctr(txns):
    print(f.account_number, f.detail)
```

## Quality gate

```
ruff check src tests          # 0 issues
ruff format --check src tests # 0 diffs
mypy --strict src             # 10 source files clean
pytest                        # 117 tests, all green
```

## License

MIT
