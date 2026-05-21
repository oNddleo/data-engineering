# vn-school-grade-pipeline

VN secondary-school grade classifier per MOET Circular 22/2021.

## What it does

* **`SubjectScore`** — one subject, score on the VN 10-point scale
  with one-decimal precision validation.
* **`SemesterReport`** — bundle of subject scores + conduct rating
  for a term. Duplicate subjects rejected.
* **`classify(report)`** — bucket the report into Tốt / Khá / Đạt /
  Chưa đạt per the per-subject threshold rules.
* **`gpa(report)`** — arithmetic mean of subject scores.

## Quick start

```bash
pip install vn-school-grade-pipeline
vngrade info
vngrade simulate --n 1000 --seed 0 --output reports.jsonl
vngrade classify --input reports.jsonl --output classified.jsonl
vngrade summarize --input reports.jsonl
# → {"n_reports": 1000, "avg_gpa": 6.83, "by_classification": {"Tot": 142, ...}}
```

## Classification rules (simplified)

| Tier            | Conditions                                                         |
| --------------- | ------------------------------------------------------------------ |
| Tốt (Excellent) | min ≥ 6.5 + ≥1 core subject ≥ 8.0 + conduct ≥ Khá                   |
| Khá (Good)      | min ≥ 5.0 + ≥6 subjects ≥ 6.5 (or ≥ n−2)                            |
| Đạt (Pass)      | min ≥ 3.5 + ≤1 subject < 5.0                                       |
| Chưa đạt (Fail) | anything else                                                      |

Conduct override: `ChuaDat` conduct caps classification at `Đạt`
regardless of academic performance.

## Library

```python
from vngrade import (
    SemesterReport, SubjectScore, ConductRating, classify, gpa,
)

r = SemesterReport(
    student_id="S-001",
    school_year="2025-2026",
    semester=1,
    conduct=ConductRating.EXCELLENT,
    subjects=(
        SubjectScore(subject="Math", score=9.0),
        SubjectScore(subject="Literature", score=8.5),
        SubjectScore(subject="English", score=8.0),
        # ...
    ),
)
print(classify(r).value)  # → "Tot"
print(round(gpa(r), 2))    # → 8.50
```

## Caveats

* The classification rules here are a **simplification** of Circular
  22's full text. Real implementations need the chronic-absence rule,
  the make-up-exam re-classification logic, and the K12 vs K9 vs K12
  variation in the conduct threshold.
* "Core subjects" are hard-coded to Math / Literature / English in
  both their English and pinyin-romanised forms (Toan, Van, TiengAnh).
  Bind your upstream schema to one form.

## License

MIT.
