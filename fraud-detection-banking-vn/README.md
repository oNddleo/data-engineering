# fraud-detection-banking-vn

Real-time fraud detection cho internet banking Việt Nam — detect
các pattern lừa đảo phổ biến (giả Công An, "chuyển khoản nhầm",
đầu tư crypto, việc nhẹ lương cao, vay nhanh) qua phân tích
narrative tiếng Việt + behavioural signals. Latency budget < 200ms;
thực tế đo được ~0.01ms p50.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

Mỗi giao dịch user xác nhận trên app banking đi qua `FraudEngine.evaluate(req)`
và nhận lại quyết định **ALLOW / REVIEW / BLOCK** trong < 200ms.
Engine combine 8 signal types:

| Signal                      | Points | Why                                                        |
| --------------------------- | ------ | ---------------------------------------------------------- |
| `BLACKLIST_BENEFICIARY`     | 100    | Beneficiary in known-mule list → instant block             |
| `KEYWORD_CONG_AN_IMPERSONATION` | 55 | Narrative contains "công an", "điều tra", "viện kiểm sát"   |
| `KEYWORD_CRYPTO_FOREX_SCAM` | 40     | "crypto", "bitcoin", "đầu tư sinh lời cao"                  |
| `OTP_RACE`                  | 35     | OTP verified < 10s after issuance (scammer reading SMS)     |
| `BENEFICIARY_HOT`           | 35     | Beneficiary receiving from ≥ 5 distinct sources in 1h       |
| `KEYWORD_WRONG_TRANSFER_SCAM` | 35   | "chuyển nhầm", "hoàn lại", "gửi lại"                       |
| `KEYWORD_JOB_SCAM`          | 30     | "việc nhẹ lương cao", "tuyển CTV online"                   |
| `NEW_BENEFICIARY_LARGE`     | 25     | First transfer to this beneficiary AND amount > 5M VND      |
| `KEYWORD_LOAN_SCAM`         | 25     | "vay nhanh", "vay tiền online", "app vay"                  |
| `VELOCITY_BURST`            | 25     | > 5 outgoing in last 5 minutes from same account            |
| `ROUND_AMOUNT_BELOW_10M`    | 15     | Amount in 9.5M–10M structuring band                         |
| `NIGHT_TRANSFER`            | 10     | Transfer between 23:00 and 05:00 local time                 |

Decision tiers:
* `score < 50` → **ALLOW**
* `50 ≤ score < 100` → **REVIEW** (human review queue)
* `score ≥ 100` → **BLOCK** (hard reject)

A single CRIT signal (blacklist hit at 100) blocks on its own. A
single CONG_AN match (55) lands in REVIEW. Multiple weak signals
stack: e.g. KEYWORD_CONG_AN (55) + OTP_RACE (35) + ROUND_BELOW (15) =
105 → BLOCK.

## Vietnamese text handling

The narrative-keyword matcher robustly handles all the ways Vietnamese
text can be written. `Công An`, `cong an`, `CÔNG AN`, `Công an`,
`công an` all match the same `cong an` keyword. Implementation:

1. Replace `đ` / `Đ` → `d` (NFD doesn't decompose them).
2. `unicodedata.normalize("NFD", text)`.
3. Filter out combining characters.
4. Lower-case.

All five scam-keyword categories use the plain-ASCII canonical form
internally, then `find_scam_keywords(narrative)` normalises the
narrative once and does substring matching.

## Components

| Module              | Role                                                              |
| ------------------- | ----------------------------------------------------------------- |
| `fraudvn.schema`    | `TransactionRequest`, `Decision`, `SignalHit`, `FraudDecision`     |
| `fraudvn.keywords`  | `normalize_vn_text`, 5 scam-keyword categories, weight map         |
| `fraudvn.state`     | `AccountState`, `StateStore` — per-account beneficiary/velocity   |
| `fraudvn.signals`   | 8 signal-detector functions with explicit thresholds              |
| `fraudvn.engine`    | `FraudEngine.evaluate()` orchestrator + latency measurement       |
| `fraudvn.io_jsonl`  | JSONL codec for requests + decisions                              |
| `fraudvn.simulator` | Seeded synthetic stream with controllable scam injection          |
| `fraudvn.cli`       | `fraudvn info | simulate | evaluate`                              |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
fraudvn info

# 1) Synthesise a stream with multiple scam categories injected.
fraudvn simulate \
  --benign 50 \
  --inject-scams cong_an,crypto,chuyen_nham \
  --blacklist-n 1 --velocity 1 --otp-race 1 \
  --blacklist BAD-ACCOUNT-001 \
  --seed 42 \
  --output stream.jsonl

# 2) Evaluate the stream + report decision counts + latency percentiles.
fraudvn evaluate \
  --input stream.jsonl \
  --blacklist BAD-ACCOUNT-001 \
  --output decisions.jsonl \
  --summary
```

End-to-end on a mixed synthetic stream:

```
$ fraudvn evaluate --input fr.jsonl --blacklist BAD-001 --summary
wrote 31 decisions to dec.jsonl
Summary: 31 txns — {'ALLOW': 27, 'REVIEW': 3, 'BLOCK': 1}
latency p50/p95/max ms: 0.008 / 0.038 / 0.230
```

p50 = 0.008ms, p95 = 0.038ms, max = 0.230ms — **three orders of
magnitude under the 200ms SLO**.

## Library

```python
from fraudvn import FraudEngine, TransactionRequest, Channel
from datetime import datetime
from fraudvn.schema import VN_TZ

engine = FraudEngine(blacklist={"BAD-ACCOUNT-001"})

req = TransactionRequest(
    txn_id="TXN-1",
    initiator_account="ACC-INITIATOR",
    beneficiary_account="ACC-BENEFICIARY",
    beneficiary_bank_bin="970418",
    amount_vnd=50_000_000,
    narrative="Chuyển khoản theo yêu cầu Công An phục vụ điều tra",
    channel=Channel.MOBILE_APP,
    occurred_at=datetime(2026, 5, 14, 14, 0, tzinfo=VN_TZ),
)

decision = engine.evaluate(req)
print(decision.decision.value, decision.score, f"{decision.latency_ms:.3f}ms")
for s in decision.signals:
    print(f"  +{s.points}  {s.name}: {s.detail}")
```

Output:

```
REVIEW 55 0.027ms
  +55  KEYWORD_CONG_AN_IMPERSONATION: narrative matches CONG_AN_IMPERSONATION: cong an, dieu tra
```

## Scam-keyword reference (VN context)

Curated from State Bank of Vietnam fraud-warning advisories
(2024–2025) + Bộ Công An press releases:

* **Giả danh Công An / Viện Kiểm Sát** — kẻ gian gọi điện giả công an
  yêu cầu chuyển tiền "phục vụ điều tra"
* **Chuyển khoản nhầm** — kẻ gian gửi tiền vào tài khoản nạn nhân
  với nội dung "chuyển nhầm", sau đó yêu cầu chuyển lại vào tài
  khoản khác (rút lại đơn tiếp khi tiền gửi từ ngân hàng khác)
* **Đầu tư crypto / forex / sàn ABC** — dụ đầu tư lãi cao
* **Việc nhẹ lương cao / Tuyển CTV** — yêu cầu nạp tiền để "kích
  hoạt" đơn hàng
* **Vay tiền online / App vay** — vay với lãi suất cao, đòi đặt cọc
  trước

## Quality

```bash
make test       # 106 tests, 6 Hypothesis properties
make type       # mypy --strict
make lint
```

- **106 tests** including 6 Hypothesis properties:
  - `score_to_decision` is total on all non-negative integers
  - Above-block-threshold scores always BLOCK
  - Below-review-threshold scores always ALLOW
  - TransactionRequest round-trips through JSONL for any amount
  - `normalize_vn_text` is idempotent (`normalize(normalize(x)) == normalize(x)`)
  - Clean short narrative + small amount + day-time → ALLOW
- mypy `--strict` clean over 9 source files; ruff + ruff-format
  clean.
- Multi-stage slim Docker image, non-root `fraud` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
