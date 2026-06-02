# Changelog

## 0.1.0 — 2026-05-20

Initial production-grade release.

* **Token bucket** — `allow(bucket, key, now_ms)` with monotonic time;
  refills at `rate_per_sec`, caps at `capacity`.
* **Leaky bucket** — `allow(bucket, key, now_ms)` with `queue_depth`;
  drains at `rate_per_sec`, refuses when full.
* **Sliding window log** — `allow(limiter, key, now_ms)` with
  `current_count`; evicts via binary search; O(capacity) memory per key.
* **Simulator** — constant-rate + burst-then-idle generators.
* **CLI** — `info | bench`.
* **Quality gate** — 46 tests with Hypothesis property tests (burst
  capped at capacity, key isolation); mypy --strict clean.
