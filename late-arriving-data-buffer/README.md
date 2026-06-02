# late-arriving-data-buffer

**Streaming primitive** for event-time pipelines: buffer events by
event-time, advance a watermark, emit in event-time order, dead-letter
events that arrive after their watermark has passed. Implements three
canonical watermark generation strategies (Heuristic, Periodic,
Punctuated) and exposes per-run metrics (drop rate, lateness
percentiles).

Pure-Python, zero dependencies.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Accepts** events carrying `event_id` + `event_time` + `ingest_time`
   + opaque `payload`. Rejects naive datetimes and ingest-before-event
   at construction.
2. **Buffers** events in an event-time-keyed min-heap, then **emits**
   them in event-time order when the watermark advances past them.
3. **Generates the watermark** via one of three strategies — Beam /
   Flink-style bounded-out-of-orderness (heuristic), tick-driven
   (periodic), or marker-driven (punctuated).
4. **Dead-letters** events arriving after their watermark has passed,
   capturing the lateness as a `lateness_seconds` field for downstream
   ops review.
5. **Deduplicates** on `event_id` (idempotent input).
6. **Reports** per-run stats: drop rate, max/median/p99 lateness,
   final watermark — pure functions of the buffer instance, no
   external dependencies.

## Watermark strategies

| Strategy        | Watermark advances when…                                          |
| --------------- | ----------------------------------------------------------------- |
| `HEURISTIC`     | every event, to `max(event_time_seen) - allowed_lateness`.        |
| `PERIODIC`      | every `tick_seconds` in processing-time (silent between ticks).   |
| `PUNCTUATED`    | the arriving event has `is_punctuation=True`.                     |

The Heuristic strategy is the default — same as
[Flink's BoundedOutOfOrdernessWatermark](https://nightlies.apache.org/flink/flink-docs-release-1.19/docs/dev/datastream/event-time/built_in/)
and Apache Beam's `WithTimestamps`.

## Event lifecycle

```
                  buffer.accept(e)
                       │
                       ▼
              ┌────────────────┐
              │  Late?         │ ─── yes ──► DEAD_LETTERED (record + drop)
              └────────────────┘
                       │ no
                       ▼
                  heap.push(e)
                       │
                       ▼
              watermark.update(e)
                       │
                       ▼
              ┌────────────────┐
              │  advance > 0?  │ ─── no ───► (event stays buffered)
              └────────────────┘
                       │ yes
                       ▼
              drain heap below watermark
                       │
                       ▼
                  EMITTED (in event-time order)
```

`buffer.flush()` at end-of-stream forces watermark advance and emits
everything remaining.

## Components

| Module             | Role                                                                |
| ------------------ | ------------------------------------------------------------------- |
| `latebuf.schema`   | `Event`, `BufferConfig`, `BufferStats`, `EmittedRecord`, `WatermarkStrategy`, `EventDisposition` |
| `latebuf.watermark`| `WatermarkState.update()` implements all three strategies            |
| `latebuf.buffer`   | `LateArrivingBuffer` — heap-backed reordering + dead-letter           |
| `latebuf.metrics`  | `compute_stats()` — drop rate + lateness percentiles                  |
| `latebuf.simulator`| Seeded synthetic streams with `BOUNDED` or `HEAVY_TAIL` lateness     |
| `latebuf.io_jsonl` | Type-checked JSONL codec for events, emits, stats                    |
| `latebuf.cli`      | `latebuf info \| simulate \| run \| summary`                         |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
latebuf info
latebuf simulate --events 500 --distribution HEAVY_TAIL --max-lateness 30 --p95 5 \
                  --seed 7 --output events.jsonl
latebuf run --input events.jsonl --strategy HEURISTIC --allowed-lateness 10 \
            --output emits.jsonl --show
latebuf run --input events.jsonl --strategy PERIODIC --tick 5 --allowed-lateness 10 --show
latebuf run --input events.jsonl --strategy PUNCTUATED --allowed-lateness 0 --show
latebuf summary --input events.jsonl --allowed-lateness 10
```

Sample `run --show` (heavy-tail simulator, allowed_lateness=5s):

```
strategy:         HEURISTIC
allowed_lateness: 5s
n_accepted:       500
n_emitted:        471
n_dead_lettered:  29
n_still_buffered: 0
drop_rate:        5.8%
max_lateness:     24s
median_lateness:  12s
p99_lateness:     24s
```

Sample `summary` (PERIODIC, allowed_lateness=10s, tick=5s):

```json
{
  "n_accepted": 500,
  "n_emitted": 480,
  "n_dead_lettered": 20,
  "n_still_buffered": 0,
  "max_lateness_seconds": 16,
  "median_lateness_seconds": 7,
  "p99_lateness_seconds": 16,
  "final_watermark": "2026-05-18T09:08:06+07:00",
  "drop_rate_pct": 4.0
}
```

`latebuf run` exits **2** when any event was dead-lettered (so the
command can be used as a CI / Airflow gate).

## Library

```python
from datetime import timedelta
from latebuf.buffer    import LateArrivingBuffer
from latebuf.metrics   import compute_stats
from latebuf.schema    import BufferConfig, EventDisposition, WatermarkStrategy
from latebuf.simulator import generate

events = generate(n_events=500, seed=7, max_lateness_seconds=30)

buf = LateArrivingBuffer(BufferConfig(
    strategy=WatermarkStrategy.HEURISTIC,
    allowed_lateness=timedelta(seconds=10),
))
emitted = []
for e in events:
    emitted.extend(buf.accept(e))
emitted.extend(buf.flush())

on_time = [r for r in emitted if r.disposition is EventDisposition.EMITTED]
late    = [r for r in emitted if r.disposition is EventDisposition.DEAD_LETTERED]
stats   = compute_stats(buf)
print(f"emitted {len(on_time)} on time, dead-lettered {len(late)}; "
      f"drop_rate={stats.drop_rate_pct:.1f}%")
```

## Key design decisions

- **Min-heap-backed reordering.** All buffered events sit in a
  `heapq` keyed by `(event_time, event_id)`. The tie-breaker on
  `event_id` makes output deterministic across runs even when
  multiple events share an exact event-time.
- **Idempotent input via `event_id` dedup.** A re-delivered event
  (same `event_id`) is silently dropped — matches Kafka exactly-once
  / Flink keyed-state conventions.
- **Heuristic is the default.** It's what Beam/Flink ship with,
  and reacts to every event without needing periodic timers. Periodic
  exists for systems where downstream prefers fewer, larger steps.
  Punctuated exists for sources with explicit batch markers (file
  rolls, CDC commits, EOF sentinels).
- **`flush()` is mandatory at end-of-stream.** Without it, events
  with event-time > final watermark stay buffered forever. The CLI
  always calls flush before reporting stats.
- **Lateness measured against the watermark at arrival time.** Not
  against the final watermark. This is what real ops dashboards
  show — "this event was N seconds too late to be processed".
- **Schema validates at construction.** `ingest_time < event_time`
  is impossible (would mean the buffer received the event before
  it occurred). Naive datetimes are rejected. Catches bugs at
  source-side schema mapping, not deep in the pipeline.
- **CI exit codes:** `latebuf run` exits **2** when any event was
  dead-lettered — suitable for shell scripting / Airflow gates.

## Quality

```bash
make test       # 71 tests + 8 Hypothesis properties
make type       # mypy --strict
make lint
```

- **71 tests**, 0 failing; 8 Hypothesis properties (buffer
  accounting always balanced; high allowed_lateness eliminates
  drops; emit stream is event-time sorted; watermark only ever
  advances forward; stats consistent with buffer counters;
  `event_id` dedup is idempotent; PUNCTUATED emits nothing without
  a punctuation; zero-events → zero stats).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `latebuf` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
