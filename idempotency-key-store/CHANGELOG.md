# Changelog

## 0.1.0

Initial release.

* `IdempotencyEntry` frozen-slots dataclass with validation
  (IN_PROGRESS must have empty body, expires_at > created_at).
* `EntryStatus` enum (IN_PROGRESS / SUCCEEDED / FAILED).
* `fingerprint()` — stable 16-hex-char SHA-256 prefix.
* `IdempotencyStore` — in-memory store with `check_or_reserve` →
  `Outcome` (NEW / REPLAY_SUCCESS / REPLAY_FAILED / IN_PROGRESS /
  CONFLICT), `finalize`, `get`, `evict_expired`.
* Lazy TTL eviction on every read; `evict_expired` for explicit
  garbage collection.
* `simulator.generate` — deterministic synthetic retry stream.
* `idemp` CLI: `info | fingerprint | simulate-run`.
* JSONL codec for `IdempotencyEntry`.
* Hypothesis property tests for fingerprint determinism, replay
  invariance, and conflict-on-different-payload.
