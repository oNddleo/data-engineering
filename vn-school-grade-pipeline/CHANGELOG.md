# Changelog

## 0.1.0

Initial release.

* `ConductRating` / `SemesterClassification` enums (Tốt / Khá / Đạt
  / Chưa đạt).
* `SubjectScore` — 10-point scale with one-decimal validation.
* `SemesterReport` — frozen dataclass with duplicate-subject rejection.
* `classify` — per-subject threshold rules + core-subject requirement
  + conduct cap.
* `gpa` — simple arithmetic mean.
* `simulator.generate` — talent-stratified synthetic report generator.
* `vngrade` CLI: `info | classify | summarize | simulate`.
* JSONL codec for `SemesterReport`.
* Hypothesis property tests for classification-in-enum,
  gpa-in-range, and conduct-fail caps invariant.
