# time-window-aggregator

Three canonical streaming window strategies in pure Python 3.10+ —
tumbling, sliding, and session windows with per-key aggregation
(count, sum, min, max, avg).

Foundational primitive in every modern streaming engine (Flink,
Kafka Streams, ksqlDB, Spark Structured Streaming). Zero runtime
deps, `mypy --strict` clean, 75 tests including Hypothesis property
tests.

## What's in the box

| Module             | Purpose                                          |
| ------------------ | ------------------------------------------------ |
| `windows.schema`   | `Window`, `Event`, `WindowedAggregate`, `WindowKind` |
| `windows.tumbling` | Fixed-size, non-overlapping windowing            |
| `windows.sliding`  | Fixed-size, overlapping windowing with stride    |
| `windows.session`  | Variable-size, gap-based windowing               |
| `windows.simulator`| Uniform + bursty event-stream generators         |
| `windows.io_jsonl` | JSONL codec                                      |
| `windows.cli`      | `info | simulate | tumbling | sliding | session | summary` |

## Quick start

```bash
python -m windows.cli simulate --keys 3 --events 100 --interval-ms 1000 --output events.jsonl
python -m windows.cli tumbling --input events.jsonl --width-ms 5000 --output aggs.jsonl
python -m windows.cli sliding  --input events.jsonl --width-ms 5000 --stride-ms 1000
python -m windows.cli session  --input events.jsonl --timeout-ms 30000
```

```python
from windows import Event, tumbling_aggregate, sliding_aggregate, session_aggregate

events = [Event(key="u1", value=v, ts_ms=ts) for ts, v in stream()]

# Per-minute rollup
per_minute = tumbling_aggregate(events, width_ms=60_000)

# Trailing 5-min recomputed every 1 min
trailing = sliding_aggregate(events, width_ms=300_000, stride_ms=60_000)

# Session-based user activity (30-min inactivity = new session)
sessions = session_aggregate(events, timeout_ms=1_800_000)
```

## Windowing semantics

| Kind     | Width | Overlap | Key-aware | Use case                                    |
| -------- | ----- | ------- | --------- | ------------------------------------------- |
| TUMBLING | fixed | none    | yes       | per-period rollups (per-minute, per-hour)   |
| SLIDING  | fixed | stride  | yes       | trailing windows (1-hr p99 every 1 min)     |
| SESSION  | varies| n/a     | yes       | user activity, request bursts               |

All windows are half-open ``[start_ms, end_ms)``.

## Quality gate

```
ruff check src tests          # 0 issues
ruff format --check src tests # 0 diffs
mypy --strict src             # 8 source files clean
pytest                        # 75 tests, all green
```

## License

MIT
