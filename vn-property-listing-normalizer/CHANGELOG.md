# Changelog

## 0.1.0

Initial release.

* `parse_price_vnd` — VN-locale price parser (`tỷ`, `triệu`, `nghìn`,
  `tr`, `k`, raw VND, comma-decimal, dot-grouped thousands).
* `parse_area_m2` — area parser with `7x10m` frontage × depth support.
* `parse_province` / `parse_district` / `parse_ward` — regex-based
  VN admin-hierarchy extractors.
* `normalize(raw) -> Listing` — end-to-end normaliser; derives
  `price_per_m2_vnd`.
* `simulator.generate` — deterministic synthetic listing generator
  (HCMC + Hanoi templates).
* `vnprop` CLI — `info | price | area | normalize | simulate`.
* JSONL codec for `Listing` and `RawListing`.
* 48 tests covering parsers, normaliser, IO, simulator, and CLI.
