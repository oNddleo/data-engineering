# vn-address-parser

Parse Vietnamese postal addresses into the 3-level administrative
hierarchy — **Tỉnh/Thành phố** → **Quận/Huyện** → **Phường/Xã**.
Bundles all **63 provinces** + central districts of the 5 directly-
managed cities. Handles real-world VN inputs: full diacritics,
diacritic-folded text, abbreviations (``Q.1``, ``P.``, ``TPHCM``),
and **Levenshtein fuzzy matching** for typo tolerance.

Pure-Python, zero dependencies.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Bundles 63 VN provinces** (5 centrally-managed cities + 58
   provinces) per Resolution 1211/2016/UBTVQH13 + post-2008
   reorganizations, with full diacritic VN names and ASCII glosses.
2. **Bundles central districts** of the 5 directly-managed cities:
   HCM (22), HN (12), DN (6) — **40 districts** in total, plus
   sample wards in HCM Q1/Q3/BT and HN HK/BD for parser testing.
3. **Normalises raw input** in three steps: lowercase → expand
   abbreviations → fold diacritics → collapse whitespace. So
   ``TP.HCM``, ``TPHCM``, ``Hồ Chí Minh``, ``Ho Chi Minh`` all
   collapse to the same canonical form.
4. **Parses an address** by walking comma-separated tokens
   right-to-left (most-specific to most-general), matching against
   PROVINCE → DISTRICT (scoped to province) → WARD (scoped to
   district). Each match attempts EXACT first, then FUZZY
   (Levenshtein ≤ 2).
5. **Tolerates typos** via Wagner-Fischer Levenshtein with
   length-difference short-circuit. ``Hà Nọi`` still resolves to
   ``Thành phố Hà Nội``.

## Administrative hierarchy

```
PROVINCE  (63 total — Tỉnh / Thành phố trực thuộc Trung ương)
   │
   ├── DISTRICT  (Quận / Huyện / Thị xã / Thành phố thuộc tỉnh)
   │       │
   │       └── WARD  (Phường / Xã / Thị trấn)
```

Province codes follow ISO 3166-2:VN where applicable; otherwise the
2-3 letter TCTK code (``HCM``, ``HN``, ``DN``, ``BV`` = Bà Rịa-Vũng
Tàu, etc).

## Match kinds

| Kind         | Meaning                                                          |
| ------------ | ---------------------------------------------------------------- |
| `EXACT`      | Normalised input == unit's diacritic-folded canonical name.      |
| `FUZZY`      | Edit distance ≤ 2 against canonical name (typo tolerance).        |
| `ABBREV`     | Resolved via abbreviation expansion (``Q.1`` → ``Quận 1``).       |
| `MISSING`    | No match found at this level.                                    |

## Components

| Module             | Role                                                                |
| ------------------ | ------------------------------------------------------------------- |
| `vnaddr.schema`    | `AdminUnit`, `AdminLevel`, `MatchedToken`, `MatchKind`, `ParsedAddress` |
| `vnaddr.units`     | Bundled directory: 63 provinces + 40 districts + sample wards       |
| `vnaddr.normalize` | Diacritic-folding, abbreviation expansion, tokenisation             |
| `vnaddr.distance`  | Wagner-Fischer Levenshtein + nearest-neighbour finder               |
| `vnaddr.parser`    | `parse(text) → ParsedAddress` — the top-level entry point           |
| `vnaddr.simulator` | Seeded synthetic addresses across 4 noise levels (CLEAN / ABBREV / FOLDED / TYPO) |
| `vnaddr.io_jsonl`  | Type-checked JSONL codec                                            |
| `vnaddr.cli`       | `vnaddr info \| parse \| batch \| normalize \| list-units \| simulate \| summary` |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
vnaddr info
vnaddr parse --text "123 Lê Lợi, Phường Bến Nghé, Quận 1, TP.HCM"
vnaddr parse --text "Hoàn Kiếm, Hà Nội" --json
vnaddr normalize --text "TP.HCM, Q.1"
vnaddr list-units --level PROVINCE
vnaddr simulate --n 100 --noise TYPO --seed 7 --output addrs.txt
vnaddr batch --input addrs.txt --output parsed.jsonl
vnaddr summary --input addrs.txt
```

Sample `parse`:

```
raw:       123 Lê Lợi, Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh
street:    123 Lê Lợi
ward:      Phường Bến Nghé (EXACT)
district:  Quận 1 (EXACT)
province:  Thành phố Hồ Chí Minh (EXACT)
complete:  True
normalised: 123 Lê Lợi, Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh
```

Same address with abbreviations + folded diacritics:

```
$ vnaddr parse --text "50 Hai Ba Trung, P. Ben Nghe, Q.1, TPHCM"
raw:       50 Hai Ba Trung, P. Ben Nghe, Q.1, TPHCM
street:    50 Hai Ba Trung
ward:      Phường Bến Nghé (EXACT)
district:  Quận 1 (EXACT)
province:  Thành phố Hồ Chí Minh (EXACT)
complete:  True
```

Fuzzy match (typo'd province):

```
$ vnaddr parse --text "Lê Lợi, Hoàn Kiếm, Hà Nọi"
ward:      -
district:  Quận Hoàn Kiếm (FUZZY)
province:  Thành phố Hà Nội (FUZZY)
complete:  False
```

Sample `summary` over 50 synthetic typo-noised addresses:

```json
{
  "n_inputs": 50,
  "complete": 50,
  "partial": 0,
  "failed": 0,
  "completion_rate_pct": 100.0,
  "matches_by_kind": {
    "EXACT": 116,
    "FUZZY": 34
  }
}
```

`vnaddr parse` exits **2** when the parse is incomplete (≥ 1 level
missing); useful as a CI / data-quality gate.

## Library

```python
from vnaddr.parser import parse

p = parse("123 Lê Lợi, Phường Bến Nghé, Quận 1, TP.HCM")
print(p.is_complete)                          # True
print(p.province.matched_code)                # "HCM"
print(p.district.matched_name)                # "Quận 1"
print(p.ward.matched_name)                    # "Phường Bến Nghé"
print(p.normalised)                           # canonical reconstruction
```

```python
# Lower-level access
from vnaddr.normalize import normalise, fold_diacritics
from vnaddr.distance  import levenshtein, find_closest

assert fold_diacritics("Đà Nẵng") == "da nang"
assert normalise("TP.HCM") == "thanh pho ho chi minh"
assert levenshtein("kitten", "sitting") == 3
print(find_closest("orage", ["orange", "garage"], max_distance=2))
# → ("orange", 1)
```

## Key design decisions

- **Bundled directory, no I/O.** All 63 provinces + 40 central
  districts ship in the wheel — consumers get a working parser
  immediately. Wards are sampled, not exhaustive; production
  callers extend with their own data source (typically the General
  Statistics Office's GSO admin-unit dump).
- **Right-to-left token walk.** VN addresses are conventionally
  ordered most-specific-to-most-general: ``"<street>, <ward>,
  <district>, <province>"``. We walk tokens right-to-left, matching
  province first, then scoping district lookup to that province,
  and ward to that district.
- **Three-stage matching:** EXACT (after normalisation) → strip
  admin prefix and retry → FUZZY (Levenshtein ≤ 2). The
  prefix-strip step handles inputs like ``"Hồ Chí Minh"`` (without
  ``Thành phố``) gracefully.
- **Wagner-Fischer with length short-circuit.** Two-row DP, O(n × m)
  worst-case but in practice ≤ 30 chars per token. The
  length-difference early-out skips obvious non-matches without
  computing the full matrix.
- **Idempotent normalisation.** ``normalise(normalise(x)) ==
  normalise(x)`` and ``fold_diacritics`` is similarly idempotent —
  property-tested.
- **CI exit codes:** `vnaddr parse` exits **2** when the parse is
  incomplete, suitable as a gate task.

## Quality

```bash
make test       # 108 tests + 10 Hypothesis properties
make type       # mypy --strict
make lint
```

- **108 tests**, 0 failing; 10 Hypothesis properties (fold
  idempotent + always lowercase; normalise idempotent;
  Levenshtein self == 0, symmetric, bounded by max length;
  find_closest returns a haystack member when match exists;
  CLEAN/FOLDED/ABBREV simulator output always fully parses;
  long consonant-garbage never matches).
- mypy `--strict` clean over 9 source files; ruff clean.
- Multi-stage slim Docker image, non-root `vnaddr` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
