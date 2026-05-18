# Changelog

## [0.1.0] — 2026-05-18

### Added
- `AdminLevel` enum with three levels (PROVINCE / DISTRICT / WARD).
- `MatchKind` enum with four match outcomes (EXACT / FUZZY /
  ABBREV / MISSING).
- `AdminUnit` frozen-slots dataclass with `code`, `name_vi`,
  `name_en`, `level`, `parent_code`, `aliases`. Validation
  enforces PROVINCE has no parent, DISTRICT/WARD have parent.
- `MatchedToken` carrying `raw_token`, `matched_code`,
  `matched_name`, `kind`, and Levenshtein `edit_distance`.
- `ParsedAddress` with `street` + optional ward/district/province
  tokens. Computed `is_complete` / `is_partial` / `normalised`
  properties.
- `vnaddr.units` — bundled directory of **63 provinces** (5
  centrally-managed cities + 58 provinces per Resolution
  1211/2016/UBTVQH13) and **40 central districts** of HCM (22),
  HN (12), DN (6). Sample wards in HCM Q1/Q3/BT and HN HK/BD.
  Lookups: `all_units()`, `by_level()`, `by_code()`, `by_parent()`,
  `n_provinces()`.
- `vnaddr.normalize`:
  - `fold_diacritics()` — replace VN diacritics with ASCII
    equivalents using a 67-char mapping table; NFC-normalises
    first to coalesce combining marks.
  - `expand_abbreviations()` — regex-driven expansion of
    ``TP.HCM`` / ``TPHCM`` → ``thành phố hồ chí minh``, ``Q.1`` /
    ``Q1`` / ``Quan 1`` → ``quận 1``, ``P. <name>`` → ``phường
    <name>``, etc.
  - `normalise()` — full pipeline: strip + lowercase + expand +
    fold + collapse whitespace. Idempotent.
  - `tokens()` — split on comma/slash, drop empty.
- `vnaddr.distance`:
  - `levenshtein()` — Wagner-Fischer two-row DP, O(min(n, m)) space.
  - `find_closest()` — nearest-neighbour over a haystack with
    length-difference early-out and configurable
    `max_distance` (default 2).
- `vnaddr.parser.parse()` — right-to-left token walk:
  PROVINCE → DISTRICT (scoped to province) → WARD (scoped to
  district). Each match: EXACT → strip admin prefix → FUZZY (≤ 2).
  Whatever precedes the first matched admin unit becomes `street`.
- `vnaddr.simulator.generate()` — seeded synthetic addresses
  across four noise levels: CLEAN (canonical), ABBREV (Q.1 / P.),
  FOLDED (no diacritics), TYPO (1-2 char substitutions).
- `vnaddr.io_jsonl` — type-checked JSONL codec for `AdminUnit`,
  `MatchedToken`, `ParsedAddress`. Rejects type confusions.
- `vnaddr.cli` — `vnaddr info | parse | batch | normalize |
  list-units | simulate | summary`. `parse` exits **2** when the
  parse is incomplete (CI gate).
- 108 unit tests + 10 Hypothesis properties; mypy `--strict` clean;
  ruff clean; multi-stage slim Docker image.

[0.1.0]: https://github.com/sophie-nguyenthuthuy/data-engineering/releases/tag/vn-address-parser-v0.1.0
