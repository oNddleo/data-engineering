# Changelog

## 0.1.0

Initial release.

* `HSCode` — 8-digit VN harmonized-system code with chapter validation.
* `Incoterm` — Incoterms 2020 enum (EXW/FOB/CFR/CIF/DAP/DDP).
* `LineItem` / `Declaration` frozen-slots dataclasses with field
  validation.
* `tariff.duty_rate_for(chapter)` / `tariff.vat_rate_for(chapter)` —
  HS-chapter-keyed rate lookups.
* `calc.compute(declaration)` — landed-cost build-up + import duty
  + VAT + VND conversion, with pro-rated freight/insurance allocation.
* `simulator.generate` — deterministic VN import-declaration generator.
* `vncustoms` CLI: `info | tariff | calc | simulate`.
* JSONL codec for `Declaration` and `DeclarationCalc`.
* Hypothesis property tests: non-negativity, CV ≥ invoice, exact
  addon allocation, export-zero invariant.
