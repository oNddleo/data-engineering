# review-sentiment-vietnamese

Vietnamese review-sentiment pipeline — a `SentimentClassifier` Protocol
with a lexicon-based baseline bundled in. Production swaps in PhoBERT /
VinAI behind the same interface; everything downstream (aggregations,
CLI, JSONL IO) works against any implementation.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

Given a stream of Shopee / Lazada / Tiki-style customer reviews, the
pipeline:

1. Normalises Vietnamese text — strips diacritics (NFD + explicit
   `đ` / `Đ` handling) and lower-cases, so `Tốt`, `tot`, `TỐT` all
   match the same lexicon entry.
2. **Clause-scoped** lexicon scoring with negator + intensifier look-back:
   `rất tốt → +2`, `không tốt → −1`, `rất không tốt → −2`. Negators don't
   escape the clause they sit in — `không nên mua, kém chất lượng` scores
   `−2`, not `0`.
3. Buckets each review into `POSITIVE / NEGATIVE / NEUTRAL` with a
   normalised confidence in `[0, 1]`.
4. Aggregates results by **seller / product / category** with Net Promoter
   percentage, average sentiment score, and average star rating.
5. Surfaces top performers and the worst offenders for ops dashboards.

## Decision tier

| Tier        | Recall   | Cost                  | When to use                                |
| ----------- | -------- | --------------------- | ------------------------------------------ |
| **Bundled** `LexiconClassifier`    | ~75–85% on short reviews | zero deps, μs per review | smoke tests, dashboards, MVP   |
| PhoBERT / VinAI (production swap)  | 92%+                     | 100 MB+ model, GPU friendly | when you need to catch sarcasm + mixed-sentiment clauses |

The bundled baseline misses constructions like `tốt nhưng chậm` (mixed
sentiment cancels to neutral) — see [`test_classifier.py`](tests/test_classifier.py)
for the exact known-miss cases. Swap in PhoBERT via the
`SentimentClassifier` Protocol when you need to catch those.

## Components

| Module                 | Role                                                                |
| ---------------------- | ------------------------------------------------------------------- |
| `sentvn.schema`        | `Review`, `SentimentResult`, `SentimentLabel`, `VN_TZ`              |
| `sentvn.lexicon`       | VN positive / negative / intensifier / negator frozensets + `normalize_vn_text` + `tokenize` |
| `sentvn.classifier`    | `SentimentClassifier` Protocol + `LexiconClassifier` baseline       |
| `sentvn.aggregations`  | `by_seller / by_product / by_category` → `Bucket` + `top_n / worst_n` |
| `sentvn.simulator`     | Seeded synthetic VN reviews with controllable sentiment mix         |
| `sentvn.io_jsonl`      | Type-checked JSONL codec for `Review` + `SentimentResult`           |
| `sentvn.cli`           | `sentvn info \| classify \| simulate \| analyse \| aggregate \| summary` |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
sentvn info
sentvn classify --text "Sản phẩm rất tốt, giao hàng nhanh"
sentvn simulate --reviews 300 --seed 7 --output reviews.jsonl
sentvn analyse  --input reviews.jsonl --output results.jsonl
sentvn aggregate --reviews reviews.jsonl --results results.jsonl --by seller --n 5
sentvn aggregate --reviews reviews.jsonl --results results.jsonl --by category --worst
sentvn summary --results results.jsonl
```

Sample classify output:

```
$ sentvn classify --text "Sản phẩm rất tốt"
label=POSITIVE score=2 confidence=1.00

$ sentvn classify --text "Không nên mua, kém chất lượng, giao hàng chậm"
label=NEGATIVE score=-2 confidence=0.50
```

Sample aggregate output:

```
key                        n    pos%    neg%    npp%  avg_score   avg★
100007                    26   76.9%   23.1%  +53.8%      +1.31   4.12
100000                    27   66.7%   25.9%  +40.7%      +0.70   3.87
100006                    28   64.3%   25.0%  +39.3%      +1.07   3.93
```

## Library

```python
from sentvn.classifier   import LexiconClassifier
from sentvn.aggregations import by_seller, top_n, worst_n
from sentvn.simulator    import generate

reviews = generate(n_reviews=500, seed=42)
clf = LexiconClassifier()
results = [clf.classify(r) for r in reviews]

buckets = by_seller(zip(reviews, results, strict=True))
print(top_n(buckets, n=5))
print(worst_n(buckets, n=5))
```

Plug in PhoBERT (or any model) by implementing the Protocol:

```python
from sentvn.classifier import SentimentClassifier
from sentvn.schema     import Review, SentimentResult, SentimentLabel

class PhoBERTClassifier:        # satisfies SentimentClassifier
    def classify(self, review: Review) -> SentimentResult:
        ...

clf: SentimentClassifier = PhoBERTClassifier()  # downstream is unchanged
```

## Scoring rules

Each clause (split on `.,;!?\n`) is scored independently with negator +
intensifier look-back:

| Text                 | Tokens                | Score | Label    |
| -------------------- | --------------------- | ----- | -------- |
| `Tốt`                | `[tot]`               | `+1`  | POSITIVE |
| `Rất tốt`            | `[rat, tot]`          | `+2`  | POSITIVE |
| `Không tốt`          | `[khong, tot]`        | `−1`  | NEGATIVE |
| `Rất không tốt`      | `[rat, khong, tot]`   | `−2`  | NEGATIVE |
| `Tốt nhưng chậm`     | `[tot, nhung, cham]`  | `0`   | NEUTRAL (mixed-sentiment limit — known miss) |

Confidence is `|score| / (n_hits × 2)`, clamped to `[0, 1]`. Zero hits
→ zero confidence (the NEUTRAL label is "no signal", not "balanced").

## Schema notes

- `rating_x100` is the star rating × 100 (4.5 ★ → `450`) — matches
  [`shopee-product-scraper-warehouse`](../shopee-product-scraper-warehouse/)
  so reviews can be joined without lossy float arithmetic.
- `posted_at` must be timezone-aware; `VN_TZ` is `UTC+7` (Asia/Bangkok).
- `SentimentResult.confidence` is validated to `[0, 1]` at construction.

## Quality

```bash
make test       # 79 tests, Hypothesis properties
make type       # mypy --strict
make lint
```

- **79 tests**, 0 failing; Hypothesis properties cover lexicon
  invariants (idempotent normalisation, tokeniser ASCII output) and
  classifier monotonicity (more positive words ⇒ non-decreasing score).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `sentvn` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
