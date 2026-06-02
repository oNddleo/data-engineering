# Changelog

## 0.1.0

Initial release.

* `DeadLetter` frozen-slots dataclass with derived `age_ms`.
* `FailureKind` enum + keyword-driven `classify()` function.
* `RetryPolicy` with `JitterMode.NONE / FULL / EQUAL`,
  `next_backoff_ms`, `should_retry`.
* `DeadLetterQueue` — append, filter by kind/topic/age,
  `counts_by_kind`, `replay(handler, kind=...)` returning
  `ReplayResult(n_replayed, n_succeeded, n_remaining)`.
* `simulator.generate` — deterministic synthetic DL stream spanning
  all failure kinds.
* `dlq` CLI: `info | classify | backoff | summarize | simulate`.
* JSONL codec for `DeadLetter`.
* Hypothesis property tests for jitter range bounds and
  no-jitter monotonicity.
