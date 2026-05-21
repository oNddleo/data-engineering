# vn-insurance-claim-pipeline

Vietnamese BHYT (health insurance) claim normaliser + payout
calculator. Models the three rules that drive coverage in real life:

1. **Card class** (`Mã đối tượng`) — base ratio: 100 % for poor/
   near-poor/children-under-6, 95 % for retirees, 80 % for employees
   and students.
2. **In-tuyến vs trái tuyến** — out-of-network gets 40 / 60 / 100 % at
   central / provincial / district hospitals.
3. **Emergency override** — emergencies count as in-network at any tier.

Final payout = `billed × (base × out_of_network_multiplier)`. Patient
co-pay = `billed − payout`.

## Quick start

```bash
pip install vn-insurance-claim-pipeline

vnbhyt simulate --n 1000 --seed 0 --output claims.jsonl
vnbhyt payout --input claims.jsonl --output payouts.jsonl
# → {"count": 1000, "total_insurance_payout_vnd": 21_345_678_901, ...}
```

## Library

```python
from datetime import date
from vnbhyt import Claim, CardClass, HospitalTier, CareType, compute

c = Claim(
    claim_id="C-001",
    patient_id="P-001",
    card_class=CardClass.EMPLOYEE,         # 80% base
    hospital_tier=HospitalTier.CENTRAL,
    care_type=CareType.OUTPATIENT,
    icd10="J18.9",                          # pneumonia
    billed_amount_vnd=10_000_000,
    visited_on=date(2026, 3, 15),
    is_in_network=False,                    # trái tuyến
)
p = compute(c)
print(p.effective_ratio)        # 0.80 * 0.40 = 0.32
print(p.insurance_payout_vnd)   # 3_200_000
print(p.patient_copay_vnd)      # 6_800_000
```

## ICD-10 validation

Loose shape check: letter + two digits + optional `.digit[s]`.
`J18.9`, `A09`, `O80.0` accepted; `J1.9`, `J18.`, `J18.A` rejected.
We don't validate against the full ICD-10 table — that's 70 000 codes
and the upstream feed should already enforce it.

## Caveats

* Coverage ratios are **illustrative** per current MOH circulars but
  the official rules carry exceptions (chronic disease lists,
  high-tech procedures, drug formulary tiers) that aren't modeled.
* No drug-formulary check, no DRG bundling, no annual ceiling
  (5× region-1 min wage cap) — those belong in a separate module.

## License

MIT.
