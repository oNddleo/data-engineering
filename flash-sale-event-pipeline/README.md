# flash-sale-event-pipeline

Event-streaming pipeline cho Shopee VN flash-sale traffic
(**11.11 / 12.12**) — watermark-based out-of-order handling,
tumbling-window aggregations per item, hot-product / stampede /
inventory-burndown detectors, observable throughput + latency
metrics.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

```
events ─► watermark ─► tumbling-window ─► detectors ─► sinks
   │                                          │
   └──────── metrics (throughput, lag, p95 latency) ────┘
```

1. **Watermark** — Flink-style `max(event_time) − max_out_of_orderness`.
   Late events bypass the aggregator and increment a counter.
2. **Tumbling window aggregator** — per-`item_id` accumulators keyed
   on `(window_start, item_id)`. Closes a window when the watermark
   crosses `window_end`.
3. **Three detectors**:
   - `detect_hot_product` — single-window views or orders above a
     threshold.
   - `StampedeDetector` — stateful per-item view-spike detector
     (10× over the prior window's baseline).
   - `detect_burndown` — inventory will hit zero within
     `horizon_seconds` at the current orders/sec rate.
4. **Sinks** — `WindowSink` and `HotnessSink` Protocols. Bundle
   `InMemoryWindowSink` / `InMemoryHotnessSink` for tests;
   production cắm Kafka producers / Redis pub-sub at the same
   interface.
5. **Metrics** — `time.perf_counter`-based throughput,
   event-time lag, processing latency (p50 / p95 / max).

## Why watermark + tumbling, not just "count per second"

Real flash-sale traffic arrives **out of order** — mobile clients
batch events, networks drop and retry, Kafka partitions interleave.
A naïve "process each second's events" approach either:

* **Drops late events** silently → undercounts hot products
* **Waits forever** for late events → unbounded memory growth

Watermarks bound the wait: "I'll wait up to `max_out_of_orderness`
seconds, then seal the window". Anything later than that gets
dropped to a side output (the late-events counter) so ops can see
the late-arrival rate and tune.

## Components

| Module                 | Role                                                                |
| ---------------------- | ------------------------------------------------------------------- |
| `flashpipe.events`     | `Event`, `EventKind` (VIEW/ADD_TO_CART/CHECKOUT/ORDER/INVENTORY)    |
| `flashpipe.watermark`  | `WatermarkTracker` — monotonic watermark + late-event detection    |
| `flashpipe.windows`    | `TumblingAggregator` + per-item `WindowState` + `WindowAggregate`  |
| `flashpipe.detectors`  | `detect_hot_product`, `StampedeDetector`, `detect_burndown`        |
| `flashpipe.metrics`    | `MetricsCollector` + `MetricsSnapshot` (throughput + lag + latency) |
| `flashpipe.sinks`      | Sink Protocols + in-memory implementations                          |
| `flashpipe.engine`     | `StreamEngine.consume_many` — full pipeline + end-of-stream flush  |
| `flashpipe.simulator`  | Seeded synthetic stream with stampede + disorder injection          |
| `flashpipe.io_jsonl`   | JSONL codec for events / aggregates / hotness events                |
| `flashpipe.cli`        | `flashpipe info | simulate | run`                                   |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
flashpipe info

# 1) Generate synthetic flash-sale traffic with a stampede on item 100005.
flashpipe simulate \
  --events 5000 --items 20 \
  --stampede-item 100005 \
  --disorder 0.05 \
  --seed 42 \
  --output events.jsonl

# 2) Run the engine + write window aggregates + hotness events.
flashpipe run \
  --input events.jsonl \
  --window 1 \
  --oo 5 \
  --stampede-mul 5 \
  --output-windows windows.jsonl \
  --output-hotness hotness.jsonl
```

Sample throughput output (500 baseline + 200 stampede = 700 events,
single-threaded Python):

```
{
  "n_aggregates": 51,
  "n_hotness_events": 0,
  "metrics": {
    "n_events": 700,
    "n_late_events": 0,
    "throughput_events_per_sec": 58843,
    "latency_ms_p50": 0.007,
    "latency_ms_p95": 0.021,
    "latency_ms_max": 0.563
  }
}
```

**58k events/s single-thread**. The original Kafka+Spark version
targets 100k/s across a cluster; this Protocol-based engine handles
the per-partition logic — production deploys N instances behind a
Kafka consumer group with one partition per instance.

## Library

```python
from flashpipe import StreamEngine, generate, InMemoryWindowSink, InMemoryHotnessSink

events = generate(seed=42, n_events=5000, n_items=20, inject_stampede_item=100005)
engine = StreamEngine(
    window_seconds=1, max_out_of_orderness_seconds=5,
    hot_min_views=100, hot_min_orders=10,
    stampede_multiplier=5.0, stampede_min_baseline=2,
)
ws = InMemoryWindowSink()
hs = InMemoryHotnessSink()
engine.consume_many(events, window_sink=ws, hotness_sink=hs)

snap = engine.snapshot()
print(f"throughput: {snap.throughput_events_per_sec:.0f} events/s")
print(f"latency p95: {snap.latency_ms_p95:.3f} ms")
for h in hs.received:
    print(f"{h.kind.value} on item {h.item_id}: {h.detail}")
```

## Why detector defaults differ between CLI and tests

The bundled defaults (`hot_min_views=1000`, `stampede_min_baseline=10`)
are tuned for **production traffic volumes** where each item gets
hundreds of views/sec during 11.11. Tests use lower thresholds
(`min_baseline=2`, `multiplier=5`) because synthetic baseline density
is too low to satisfy production defaults — but the **detector
logic is the same**.

Production should re-tune based on observed item-popularity
distribution: items in the long tail won't hit any threshold,
which is correct (they're not hot).

## End-of-stream flush

The engine's `consume_many` calls `flush_all()` on the aggregator
at end-of-stream, **and** runs the hot/stampede detectors over the
flushed aggregates. Without this, a stampede landing in the final
window (no follow-up event to advance the watermark past it) would
silently drop its hotness alert. The fix was the most interesting
bug found during development — `test_engine_flush_at_end_of_stream`
+ the simulator's stampede test together catch it.

## Quality

```bash
make test       # 81 tests, 5 Hypothesis properties
make type       # mypy --strict
make lint
```

- **81 tests** covering event invariants, watermark monotonicity +
  lateness, tumbling-window arithmetic + per-item separation, all
  three detectors with edge cases, throughput + latency metrics,
  JSONL codec, simulator + integration, CLI, and 5 Hypothesis
  properties (round-trip, watermark monotonic over arbitrary
  delta sequences, window-start alignment, etc.).
- mypy `--strict` clean over 11 source files; ruff + ruff-format
  clean.
- Multi-stage slim Docker image, non-root `flash` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
