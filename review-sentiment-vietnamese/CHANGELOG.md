# Changelog

## [0.1.0] — 2026-05-15

### Added
- `Review`, `SentimentResult`, `SentimentLabel` (POSITIVE / NEGATIVE
  / NEUTRAL) — frozen-slots dataclasses with validation at
  construction (rating in `[0, 500]`, timezone-aware `posted_at`,
  confidence in `[0, 1]`).
- VN sentiment lexicon — 18 positive + 17 negative + 6 intensifier
  + 5 negator entries, all ASCII after diacritic stripping.
- `normalize_vn_text` — NFD + explicit `đ` / `Đ` handling, lower-case.
- `tokenize` — alphanumeric + underscore segmentation, ASCII output.
- `SentimentClassifier` Protocol; `LexiconClassifier` bundled baseline
  with clause-scoped negator + intensifier look-back.
- `score_text` splits text on `.,;!?\n` and scores each clause
  independently, so negators / intensifiers from one clause don't
  flip sentiment words in another.
- `by_seller / by_product / by_category` aggregations returning
  `Bucket` (positive/negative/neutral counts, NPP%, avg score, avg
  star rating × 100); `top_n` and `worst_n` rankers.
- Seeded synthetic VN review generator (`simulator.generate`) with
  controllable positive / negative / negated-positive / neutral mix
  for stress-testing classifier recall.
- Type-checked JSONL codec for `Review` + `SentimentResult` with
  `_require_str` / `_require_int` decoders.
- CLI `sentvn info | classify | simulate | analyse | aggregate | summary`.
- 79 tests including Hypothesis properties (lexicon normalisation is
  idempotent; classifier score is monotonic non-decreasing in the
  number of positive words).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `sentvn` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- Zero runtime dependencies.

### Notes
- The first cut of `score_text` ran negator look-back over the whole
  text, so `không nên mua, kém chất lượng, giao hàng chậm` scored 0
  (the `không` from clause 1 flipped `kém` in clause 3, cancelling a
  genuinely negative review). Fixed by clause-splitting on
  `.,;!?\n` before scoring.
- `cmd_classify` originally fell through to `sys.stdin.read()` on
  empty `--text`, which deadlocks under pytest output capture.
  Switched to an explicit `args.text is not None` check so
  `--text ""` short-circuits.
- The bundled lexicon classifier deliberately misses mixed-sentiment
  constructions like `tốt nhưng chậm`. Production callers swap in
  PhoBERT / VinAI via the `SentimentClassifier` Protocol —
  downstream aggregations and CLI are unchanged.
