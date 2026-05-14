# credit-scoring-pipeline-vn

Feature-engineering pipeline cho credit scoring theo chuẩn CIC
(Credit Information Center, NHNN) — point-in-time correct, encode
đầy đủ lịch sử Nhóm nợ 1–5 theo Thông tư 11/2021/TT-NHNN. Kèm
baseline rule-based score 300–900 với reason trail minh bạch.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Ingest** dữ liệu CIC dạng JSONL — `Borrower` (CCCD/CMND), các
   `CreditContract`, monthly `GroupAssessment`, `Inquiry` của các
   bank pull CIC.
2. **Engineer features** cho từng borrower **tại 1 observation_date
   cụ thể**, đảm bảo không có look-ahead bias:
   - CIC group: `current_max_group`, `worst_group_ever`, `max_group_24m`
   - Months-in-trouble: `months_in_group_2plus_24m` (distinct months)
   - Exposure: `total_outstanding_principal_vnd`, `provision_estimate_vnd`,
     `active_contracts`, `unique_lenders`
   - Tenure: `months_since_first_credit`, `months_since_last_credit_open`
   - Inquiries: `inquiries_3m`, `_6m`, `_12m`, `days_since_last_inquiry`
   - Product mix flags: `has_term_loan`, `has_mortgage`, `has_credit_card`, …
   - DTI: ước tính monthly payment per contract_type → tỷ lệ với
     monthly_income (None nếu chưa có income)
3. **Score** bằng baseline rule-based — 300–900, kèm reason trail
   (mỗi penalty/bonus được gắn tên + delta).

## Nhóm nợ CIC theo Thông tư 11/2021/TT-NHNN

| Nhóm | Tên tiếng Việt              | DPD (ngày)  | Dự phòng |
| ---- | --------------------------- | ----------- | -------- |
| 1    | Nợ đủ tiêu chuẩn            | 0–9         | 0 %      |
| 2    | Nợ cần chú ý                | 10–89       | 5 %      |
| 3    | Nợ dưới tiêu chuẩn          | 90–179      | 20 %     |
| 4    | Nợ nghi ngờ                 | 180–359     | 50 %     |
| 5    | Nợ có khả năng mất vốn      | ≥ 360       | 100 %    |

**Quy tắc kéo nhóm** (Điều 11): Khi một hợp đồng của borrower bị
chuyển sang Nhóm X, mọi hợp đồng khác của cùng borrower cũng được
xếp tự động vào ít nhất Nhóm X. Logic này được áp dụng trong
`features.extract()` — `current_max_group` phản ánh classification
mức borrower (cao nhất giữa các active contract).

## Point-in-time correctness

Mỗi feature chỉ dùng dữ liệu có timestamp ≤ `observation_date`:

* `contracts`: `opened_at ≤ obs_date` AND (`closed_at is None` OR `closed_at > obs_date`)
* `assessments`: `as_of_month ≤ first_of_month(obs_date)`
* `inquiries`: `inquired_at ≤ obs_date`
* Window 24m: `[obs_month - 23, obs_month]` — đúng 24 tháng inclusive

Test suite có 30+ test khẳng định các filter này — đặc biệt
`test_extract_filters_future_assessments` chứng minh một
`GroupAssessment` ở Nhóm 5 vào tháng 10/2026 không bao giờ ảnh
hưởng features tính tại obs_date = 14/05/2026.

## Components

| Module                | Role                                                                |
| --------------------- | ------------------------------------------------------------------- |
| `cicscore.cic_groups` | `CICGroup` (1–5), `PROVISION_RATE`, `VN_NAMES`, `group_from_days_past_due` |
| `cicscore.schema`     | `Borrower`, `CreditContract`, `GroupAssessment`, `Inquiry`, `ContractType` + date helpers |
| `cicscore.features`   | `extract(borrower, observation_date) -> FeatureVector`              |
| `cicscore.scoring`    | `baseline_score(features) -> Score` (with reason trail)             |
| `cicscore.simulator`  | Seeded generator with 3 risk profiles: `clean` / `watch` / `distressed` |
| `cicscore.io_jsonl`   | JSONL codec — round-trippable, type-checked decoders                |
| `cicscore.cli`        | `cicscore info | simulate | extract | score | inspect`              |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
cicscore info

# 1) Generate synthetic borrowers (60% clean / 25% watch / 15% distressed by default).
cicscore simulate \
  --borrowers 100 \
  --seed 42 \
  --observation-date 2026-05-14 \
  --output borrowers.jsonl

# 2) Extract features at one observation date.
cicscore extract \
  --input borrowers.jsonl \
  --observation-date 2026-05-14 \
  --output features.jsonl

# 3) Score (extract + baseline_score in one pass).
cicscore score \
  --input borrowers.jsonl \
  --observation-date 2026-05-14 \
  --output scores.jsonl

# 4) Inspect one borrower (features + score breakdown).
cicscore inspect \
  --input borrowers.jsonl \
  --observation-date 2026-05-14 \
  --borrower-id NB-000087
```

Sample inspect output for a distressed borrower:

```
=== NB-000087 @ 2026-05-14 ===
score = 320
current_max_group       = 4
worst_group_ever        = 4
max_group_24m           = 4
months_in_group_2plus_24m = 18
active_contracts        = 2
unique_lenders          = 2
total_outstanding_vnd   = 108,333,333
provision_estimate_vnd  = 54,166,666
months_since_first_credit = 23
inquiries_6m            = 4
dti_ratio               = 0.48

Score breakdown:
   -250  max_group_24m=4
    -90  months_in_group_2plus_24m=18
    -40  inquiries_6m=4
```

(Provision 54.16M / outstanding 108.33M = exactly 50 % per Thông tư 11/2021 Group 4 rate.)

## Library

```python
from datetime import date
from cicscore import (
    extract, baseline_score, generate,
)

borrowers = generate(n_borrowers=1000, seed=42, observation_date=date(2026, 5, 14))
features = [extract(b, date(2026, 5, 14)) for b in borrowers]
scores = [baseline_score(f) for f in features]

# Distribution check:
from collections import Counter
buckets = Counter("≥800" if s.score >= 800 else "700-799" if s.score >= 700 else
                  "600-699" if s.score >= 600 else "<600" for s in scores)
print(buckets)
```

## Baseline scoring rules

```
score = 700
  + 30  if months_since_first_credit >= 60
  − 50/150/250/400 for max_group_24m == 2/3/4/5
  − 5 per distinct month in group_2+ (24-month window)
  − 10 per inquiry in last 6 months
  − 50 if 0.5 < DTI <= 0.7
  − 100 if DTI > 0.7
  − 30 if unique_lenders >= 5
clip to [300, 900]
```

This is a transparent baseline, **not a production model**. The
real value is the feature pipeline; the score exists to make the
pipeline end-to-end testable and to anchor relative magnitudes.

## Quality

```bash
make test       # 99 tests, 5 Hypothesis properties
make type       # mypy --strict
make lint
```

- **99 tests** including 5 Hypothesis properties (group classification
  total; provision monotonic in group severity; score always in
  [300, 900]; group 5 provision == 100 % principal; group 1
  provision == 0).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `cic` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
