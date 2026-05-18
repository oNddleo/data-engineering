# Changelog

## [0.1.0] — 2026-05-18

### Added
- `WatermarkStrategy` enum (HEURISTIC / PERIODIC / PUNCTUATED)
  covering the three canonical generation patterns from Beam, Flink,
  and Kafka Streams.
- `EventDisposition` enum (EMITTED / BUFFERED / DEAD_LETTERED).
- `Event` frozen-slots dataclass with `event_id`, tz-aware
  `event_time` + `ingest_time`, opaque `payload`, optional
  `is_punctuation` marker. Validates non-empty id, tz-aware
  datetimes, and `ingest_time >= event_time` at construction.
- `BufferConfig` frozen-slots dataclass with `strategy`,
  `allowed_lateness` (default 60s), `periodic_tick` (default 5s).
  Validates non-negative `allowed_lateness` and positive
  `periodic_tick` when strategy is PERIODIC.
- `EmittedRecord` carrying the original event + its disposition +
  observed `lateness_seconds`.
- `BufferStats` with `n_accepted`, `n_emitted`, `n_dead_lettered`,
  `n_still_buffered`, max / median / p99 lateness seconds, final
  watermark, and computed `drop_rate_pct` / `total` properties.
- `latebuf.watermark.WatermarkState` — mutable state object with
  `update(event) -> datetime | None` (returns the new watermark
  on advance, `None` otherwise). Three strategies share the
  underlying state machine.
- `latebuf.watermark.WatermarkState.finalise()` — force-advance
  at end-of-stream so PUNCTUATED streams without any punctuation
  still flush deterministically.
- `latebuf.buffer.LateArrivingBuffer` — heap-backed reordering
  buffer with `accept(event)` and `flush()` semantics. Dead-letters
  events arriving with `event_time < current_watermark`; emits in
  event-time order with `(event_time, event_id)` tie-breaker for
  determinism. Deduplicates on `event_id` (idempotency).
- `latebuf.metrics.compute_stats(buffer)` — pure function over a
  buffer instance, computes nearest-rank lateness percentiles.
- `latebuf.simulator.generate()` — seeded synthetic stream with
  configurable `BOUNDED` (uniform [0, max_lateness]) or
  `HEAVY_TAIL` (95% in [0, p95], 5% in [p95, max]) lateness
  distributions, plus periodic punctuation markers.
- `latebuf.io_jsonl` — type-checked JSONL codec for events,
  emitted records, and stats. Rejects str-as-bool and other type
  confusions at load time.
- `latebuf.cli` — `latebuf info | simulate | run | summary`.
  `run` exits **2** when any event is dead-lettered (CI gate).
- 71 unit tests + 8 Hypothesis properties; mypy `--strict` clean;
  ruff clean; multi-stage slim Docker image.

[0.1.0]: https://github.com/sophie-nguyenthuthuy/data-engineering/releases/tag/late-arriving-data-buffer-v0.1.0
