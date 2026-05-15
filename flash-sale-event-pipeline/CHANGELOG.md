# Changelog

## [0.1.0] — 2026-05-15

### Added
- `Event` data type covering five flash-sale event kinds (VIEW,
  ADD_TO_CART, CHECKOUT, ORDER, INVENTORY_UPDATE) with strict
  invariants: positive item/shop IDs, non-negative quantity/amount,
  tz-aware datetimes. `INVENTORY_UPDATE` may have empty `user_id`
  since it's backend-emitted; all others require it.
- `WatermarkTracker` — Flink-style monotonic watermark.
  `watermark = max(observed) − max_out_of_orderness`. Never moves
  backward. `is_late(event_time)` for late-event detection.
- `TumblingAggregator` — per-`(window_start, item_id)` accumulator
  that closes windows when the watermark crosses `window_end`.
  Tracks views, add-to-cart, checkout, orders, units, GMV, and
  unique users per window. Late events go to a counter.
- `WindowAggregate` (frozen, immutable) with `conversion_pct`
  derived property.
- Three detectors:
  - `detect_hot_product` — single-window views/orders threshold.
  - `StampedeDetector` — stateful per-item view-spike comparator
    (current vs prior window).
  - `detect_burndown` — current order rate × stock → seconds-to-zero.
- `MetricsCollector` — `time.perf_counter`-based throughput,
  event-time lag (`processed_at_wall − event.created_at`), and
  processing latency. Snapshots include p50 / p95 / max via linear
  interpolation between rank positions.
- `WindowSink` / `HotnessSink` Protocols + in-memory implementations.
  Production swaps in Kafka producers / Redis pub-sub at the same
  surface.
- `StreamEngine.consume_many` — full pipeline orchestrator with
  proper end-of-stream flush that **runs detectors on flushed
  aggregates** (the most interesting bug fixed during development:
  a stampede landing in the final window silently dropped its
  alert without this).
- Seeded synthetic generator (`simulator.generate`) with
  controllable stampede injection (`inject_stampede_item`) and
  out-of-order noise (`out_of_order_fraction`).
- JSONL codec for events, aggregates, and hotness events.
- `flashpipe` CLI: `info`, `simulate`, `run` (with optional
  `--output-windows` and `--output-hotness` files).
- **81 tests** including 5 Hypothesis properties.
- mypy `--strict` clean over 11 source files; ruff + ruff-format
  clean.
- Multi-stage slim Docker image, non-root `flash` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

### Notes
- Measured throughput on a 700-event synthetic stream:
  **~58,000 events/s single-thread** in CPython. Production
  Kafka+Spark deployments target 100k+/s across a cluster — the
  pipeline logic here is per-partition, so N instances behind a
  Kafka consumer group scale linearly with partitions.
- Default detector thresholds are tuned for production volumes
  (`hot_min_views=1000`, `stampede_min_baseline=10`). Tests
  exercise the same detectors at lower thresholds because
  synthetic baseline density is too low to satisfy production
  defaults. Both readers (CLI users + test authors) need to know
  this — the README has a section explaining.
- Watermark + late-event semantics are the **right** way to handle
  out-of-order Kafka traffic. The simpler "process each second" or
  "buffer for K seconds then flush" approaches either drop late
  events silently or have unbounded memory. Watermarks bound the
  wait by `max_out_of_orderness`.
- `MetricsSnapshot.lag_ms_max` measures `processed_at_wall −
  event_time`. In the CLI test we use `wall_clock_now =
  event.created_at` (default) so lag stays 0 — production would
  pass `datetime.now(VN_TZ)` per event.
