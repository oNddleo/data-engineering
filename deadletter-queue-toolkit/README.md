# deadletter-queue-toolkit

Dead-letter-queue safety net for streaming pipelines.

* **`classify(error)`** — bucket free-text error strings into POISON /
  TRANSIENT / THROTTLED / TIMEOUT / UNKNOWN. The first three
  classifications are typically actionable; UNKNOWN is the fallback.
* **`RetryPolicy + next_backoff_ms`** — exponential backoff with
  optional full / equal / none jitter. Capped at `max_backoff_ms`.
* **`DeadLetterQueue`** — in-memory queue with selective `filter`,
  `counts_by_kind`, and `replay(handler, kind=...)` driver.

## Quick start

```bash
pip install deadletter-queue-toolkit

dlq classify "503 Service Unavailable"
# → {"error": "503 Service Unavailable", "kind": "transient"}

dlq backoff --max-attempts 5 --base-ms 100 --multiplier 2 --jitter none
# → {"schedule_ms": [100, 200, 400, 800, 1600]}

dlq simulate --n 1000 --seed 0 --output dlq.jsonl
dlq summarize --input dlq.jsonl
# → {"total": 1000, "by_kind": {"poison": 222, "transient": 218, ...}}
```

## Library

```python
from dlq import DeadLetterQueue, classify, RetryPolicy, next_backoff_ms

# Classify and route on the producer side:
kind = classify(str(exc))
# Build a backoff schedule:
policy = RetryPolicy(max_attempts=5, base_ms=100)
backoffs = [next_backoff_ms(policy, attempt) for attempt in range(5)]

# Park the failed message:
q = DeadLetterQueue()
q.append(DeadLetter(...))

# Periodic replay of recoverable failures only:
result = q.replay(handler=my_handler, kind=FailureKind.TRANSIENT)
print(result.success_rate)
```

## Backoff jitter

| Mode  | Formula                              | Best for                          |
| ----- | ------------------------------------ | --------------------------------- |
| NONE  | `backoff`                            | Deterministic tests               |
| FULL  | `uniform(0, backoff)`                | Thundering-herd protection        |
| EQUAL | `backoff/2 + uniform(0, backoff/2)`  | Predictable mean, some spread     |

Equal jitter keeps the **mean** at the configured backoff (full
jitter halves it), so it's the right default when callers reason
about expected total wait time. Full jitter wins when many clients
are retrying the same downstream and you want maximum dispersion.

## License

MIT.
