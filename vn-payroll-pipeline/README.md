# vn-payroll-pipeline

VN payroll engine — Personal Income Tax (TNCN) 7-bracket progressive
schedule, SHUI insurance (BHXH 8% / BHYT 1.5% / BHTN 1% employee +
17.5/3/1% employer), region-specific minimum wages, and per-month
payslip computation with full employer-cost rollup.

Zero runtime deps, `mypy --strict` clean, 66 tests including
Hypothesis property tests.

## What's in the box

| Module             | Purpose                                          |
| ------------------ | ------------------------------------------------ |
| `payroll.schema`   | `Employee`, `PayPeriod`, `Payslip`, `Region`, `ResidencyStatus` |
| `payroll.insurance`| BHXH/BHYT/BHTN + 4-region min wage + SHUI caps   |
| `payroll.tax`      | 7-bracket resident PIT + 20% flat non-resident   |
| `payroll.engine`   | `compute_payslip(employee, period)` end-to-end   |
| `payroll.simulator`| Seeded employee + payroll generator              |
| `payroll.io_jsonl` | JSONL codec                                      |
| `payroll.cli`      | `info | brackets | minwage | compute | simulate` |

## Quick start

```bash
python -m payroll.cli compute --employee-id E-1 --gross 30000000 --dependents 1
# → gross 30M, insurance 3.15M (10.5%), taxable 11.45M, PIT 967.5k, net 25.88M
```

## VN PIT brackets (resident)

| Tier | Monthly taxable (VND) | Rate |
| ---- | --------------------- | ---- |
| 1    | 0 – 5 000 000         | 5%   |
| 2    | 5M – 10M              | 10%  |
| 3    | 10M – 18M             | 15%  |
| 4    | 18M – 32M             | 20%  |
| 5    | 32M – 52M             | 25%  |
| 6    | 52M – 80M             | 30%  |
| 7    | > 80M                 | 35%  |

Plus personal allowance **11M/month** and dependent allowance
**4.4M/month** per registered dependent (Nghị quyết 954/2020).

Non-residents pay a flat **20% PIT** on gross VN-sourced income.

## SHUI insurance (2025 rates)

| Fund | Employee | Employer |
| ---- | -------- | -------- |
| BHXH | 8.0%     | 17.5%    |
| BHYT | 1.5%     | 3.0%     |
| BHTN | 1.0%     | 1.0%     |
| **Total** | **10.5%** | **21.5%** |

Capped at 20× region-1 min wage (4,960,000 × 20 = 99.2M) for
BHXH+BHYT; BHTN cap is region-specific.

## Quality gate

```
ruff check src tests          # 0 issues
ruff format --check src tests # 0 diffs
mypy --strict src             # 8 source files clean
pytest                        # 66 tests, all green
```

## License

MIT
