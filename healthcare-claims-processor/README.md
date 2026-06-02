# healthcare-claims-processor

VN **BHYT** (Bảo hiểm y tế — social health insurance) claims processor.
Validates 15-character VSS card numbers per Decision 1351/QĐ-BHXH,
looks up Vietnamese ICD-10-VN codes, applies the **Quyết định
1399/QĐ-BYT** + **Nghị định 146/2018/NĐ-CP** coverage tiers
(80% / 95% / 100% by category × care level × referral status), and
computes the insurer + patient split for each claim.

Pure-Python, zero deps, integer-VND throughout.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Validates BHYT card numbers** — 15 characters, **1 scheme letter
   + 1 priority digit + 13 region/identifier digits**. The prefix
   decodes into the diện ưu tiên (priority category) that drives the
   base coverage rate.
2. **Looks up ICD-10-VN diagnoses** — bundled subset of ~40
   most-common Vietnamese clinical diagnoses (covers >70% of
   outpatient claim volume per VSS aggregates). Sub-codes resolve
   to their parent (`E11.9` → `E11`) for billing aggregation.
3. **Applies coverage rates** per `(category, care_level, has_referral,
   same_province, emergency)` — the cross-product the real VSS
   back-end runs:
   - **Base rate** by diện ưu tiên: 100% for children / war veterans /
     poor; 95% for near-poor; 80% for regular + voluntary.
   - **Referral penalty** for bypassing the chain (TƯ without
     referral → 40%; TỈNH without referral → 60%; HUYỆN / XÃ no
     penalty). Cross-province visits trigger the penalty even
     **with** a referral, unless emergency.
4. **Computes the reimbursement**: `insurer_pays = subtotal × base
   × penalty / 10_000²` with banker's rounding to nearest VND.
   `patient_pays = subtotal − insurer_pays`.
5. **Flags discrepancies** — line-total math errors, header subtotal
   mismatch, invalid card format — as notes on the result without
   rejecting the claim outright (matches VSS's tolerance for
   noisy hospital billing systems).

## BHYT card format (per VSS Decision 1351/QĐ-BHXH 2015)

```
D 4 0179 012345678
↑ ↑  ↑      ↑
│ │  │      └── 11-digit identifier
│ │  └──────── 2-digit province code
│ └──── priority digit (1-5)
└────── scheme letter
```

| Scheme | Meaning                                       |
| ------ | --------------------------------------------- |
| D      | Doanh nghiệp (employer-paid) — most common    |
| H      | Học sinh / Sinh viên (student)                |
| T      | Trẻ em (child under 6)                        |
| C      | Cận nghèo (near-poor household)               |
| G      | Gia đình (voluntary / family)                 |
| X      | Xã hội bảo trợ (social protection)            |

| Priority | Diện ưu tiên (Article 22 of the Law on Health Insurance) |
| -------- | --------------------------------------------- |
| 1        | Children < 6, ethnic minorities in poor zones |
| 2        | War veterans, revolution contributors          |
| 3        | Poor / near-poor households                    |
| 4        | Regular workers (employer-paid)                |
| 5        | Voluntary (self-paid)                          |

## Coverage matrix

| Diện | Base | At TU (correct referral) | At TU (no referral) | At TINH (no referral) | At HUYEN |
| ---- | ---- | ------------------------ | ------------------- | --------------------- | -------- |
| 1    | 100% | 100%                     | 40%                 | 60%                   | 100%     |
| 2    | 100% | 100%                     | 40%                 | 60%                   | 100%     |
| 3    | 95%  | 95%                      | 38%                 | 57%                   | 95%      |
| 4    | 80%  | 80%                      | 32%                 | 48%                   | 80%      |
| 5    | 80%  | 80%                      | 32%                 | 48%                   | 80%      |

## Components

| Module             | Role                                                                |
| ------------------ | ------------------------------------------------------------------- |
| `bhyt.schema`      | `Patient`, `BHYTCard`, `Claim`, `ClaimItem`, `Diagnosis`, `ExemptionCategory`, `CareLevel`, `ServiceKind`, `Reimbursement` |
| `bhyt.card`        | 15-char format validator + prefix decoding (6 schemes × 5 priorities) |
| `bhyt.icd10vn`     | ~40 bundled ICD-10-VN codes with VI + EN names; subcode → parent fallback |
| `bhyt.coverage`    | Base rate per category + referral-penalty multiplier table          |
| `bhyt.calculator`  | `calculate(claim, emergency=False) → Reimbursement` with banker's-rounded VND math |
| `bhyt.simulator`   | Seeded synthetic patients + cards + claims                            |
| `bhyt.io_jsonl`    | Type-checked JSONL codec for all record types                          |
| `bhyt.cli`         | `bhyt info \| simulate \| decode \| icd \| calc \| summary`           |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
bhyt info
bhyt simulate --patients 30 --claims 60 --seed 7 --out-dir ./claims
bhyt decode   D40179012345678               # decode a card number
bhyt icd      I10                            # lookup an ICD-10-VN code
bhyt icd      E11.9                          # subcode → parent fallback
bhyt calc     --input ./claims/claims.jsonl --output ./reimb.jsonl --show 5
bhyt calc     --input ./claims/claims.jsonl --output ./reimb.jsonl --emergency
bhyt summary  --input ./claims/claims.jsonl
```

Sample `calc --show 5` output:

```
claim              subtotal   cov%   pen%      insurer    patient notes
CL-000000           410,000  80.0% 100.0%      328,000     82,000
CL-000001           137,500  80.0%  60.0%       66,000     71,500
CL-000002           397,500  95.0% 100.0%      377,625     19,875
CL-000003           546,000  95.0%  60.0%      311,220    234,780
CL-000004           642,500  80.0% 100.0%      514,000    128,500
```

Sample `summary`:

```json
{
  "n_claims": 60,
  "subtotal_vnd_total": 27397500,
  "insurer_pays_vnd_total": 21821785,
  "patient_pays_vnd_total": 5575715,
  "share_paid_by_insurer_pct": 79.6,
  "by_category": {"UU_TIEN_1": 7, "UU_TIEN_2": 8, "UU_TIEN_3": 11, "UU_TIEN_4": 23, "UU_TIEN_5": 11},
  "by_care_level": {"HUYEN": 19, "OTHER": 6, "TINH": 19, "TU": 12, "XA": 4}
}
```

## Library

```python
from bhyt.calculator import calculate
from bhyt.simulator  import generate
from bhyt.card       import decode_prefix

_, _, claims = generate(n_patients=30, n_claims=60, seed=42)
for claim in claims:
    info = decode_prefix(claim.card_number)
    result = calculate(claim, emergency=False)
    print(info.category.value, claim.care_level.value,
          claim.subtotal_vnd, result.insurer_pays_vnd)
```

## Key design decisions

- **Card format follows VSS Decision 1351/QĐ-BHXH 2015**: 1 letter +
  1 digit + 13 digits. Earlier drafts assumed "2 letters + 13 digits"
  but the priority position is a digit (1-5), not a letter. The
  schema validator enforces the corrected format.
- **Sub-code ICD lookup falls back to parent**: `E11.9` (T2DM with
  no complications) maps to `E11` for billing. This mirrors how
  VSS's claims back-end de-specifies subcodes for payment aggregation.
- **Cross-province + no-referral are both penalty triggers** at
  TU/TINH levels, but **emergency overrides everything** (Article 22 §3).
  The calculator exposes `emergency=True` as an opt-in to waive the
  penalty per-claim.
- **Findings, not exceptions.** Bad line math or header-subtotal
  mismatch flags the result with notes without zeroing out the
  reimbursement. Matches VSS's real-world tolerance for noisy
  hospital billing systems.
- **Banker's rounding on integer-VND** — same convention as the
  rest of the catalogue (`vn-tax-invoice-validator`,
  `electricity-meter-iot-pipeline`). Eliminates float drift over
  multi-year audit trails.
- **No K-DRG bundling yet** — inpatient claims use the same
  per-line math as outpatient. Production callers using K-DRG
  layer their bundle prices upstream and feed the bundled rate
  in as a single line.

## Quality

```bash
make test       # 89 tests + 7 Hypothesis properties
make type       # mypy --strict
make lint
```

- **89 tests**, 0 failing; 7 Hypothesis properties (any valid-format
  card always decodes; any unknown scheme letter is always rejected;
  base rates always in `[0, 10000]` bps; effective rate components
  always in `[0, 10000]` bps; `insurer + patient == subtotal` for
  any claim; insurer pay always in `[0, subtotal]`; emergency calc
  always pays ≥ non-emergency).
- mypy `--strict` clean over 9 source files; ruff clean.
- Multi-stage slim Docker image, non-root `bhyt` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
