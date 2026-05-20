# rate-limiter-toolkit

Three canonical rate-limiter algorithms in pure Python 3.10+ — token
bucket, leaky bucket, and sliding-window log. Each keyed by an
arbitrary string so one limiter instance can throttle many users.

Zero runtime deps, `mypy --strict` clean, 46 tests including
Hypothesis property tests.

## What's in the box

| Module                    | Algorithm                                  |
| ------------------------- | ------------------------------------------ |
| `ratelimit.token_bucket`  | Capacity + refill rate, allows bursts      |
| `ratelimit.leaky_bucket`  | Queue + drain rate, smooths bursts         |
| `ratelimit.sliding_window`| Sliding-log, exact count in trailing window |
| `ratelimit.simulator`     | Constant-rate + burst-then-idle generators |
| `ratelimit.cli`           | `info | bench`                            |

## Quick start

```python
from ratelimit import TokenBucket, token_allow

tb = TokenBucket(capacity=10, rate_per_sec=5.0)
for now_ms in range(0, 10_000, 100):
    if token_allow(tb, key="user-42", now_ms=now_ms):
        handle_request()
    else:
        return 429  # Too Many Requests
```

```bash
# Benchmark each algorithm on a synthetic stream
python -m ratelimit.cli bench --algorithm token --capacity 10 --rate 5 \
  --keys 3 --requests 100 --interval-ms 100
# → admit_rate: 0.6, n_admitted: 60, n_throttled: 40
```

## Algorithm comparison

| Algorithm    | Burst behavior     | Smoothing | Memory/key | Boundary artifact |
| ------------ | ------------------ | --------- | ---------- | ----------------- |
| Token bucket | Up to capacity     | No        | O(1)       | No                |
| Leaky bucket | Up to capacity     | Yes       | O(1)       | No                |
| Sliding log  | Up to capacity     | No        | O(capacity)| No                |

## Quality gate

```
ruff check src tests          # 0 issues
ruff format --check src tests # 0 diffs
mypy --strict src             # 7 source files clean
pytest                        # 46 tests, all green
```

## License

MIT
