# idempotency-key-store

At-most-once execution via idempotency keys with TTL. The pattern
behind Stripe's `Idempotency-Key` header.

## Why

When a client sends a write and gets a network error, they don't
know whether the server applied the change. Retrying naïvely can
double-charge, double-ship, or double-post. The fix: client picks an
idempotency key once per logical operation; server caches the
`(key, fingerprint, response)` tuple so retries return the cached
result instead of re-executing.

## API

```python
from idempotency import IdempotencyStore, Outcome, EntryStatus, fingerprint

store = IdempotencyStore()

# Check or reserve atomically:
fp = fingerprint(request_body)
result = store.check_or_reserve(key="op-42", request_fingerprint=fp, now_ms=now)

if result.outcome == Outcome.NEW:
    response = do_the_thing(request_body)
    store.finalize("op-42", response, EntryStatus.SUCCEEDED, now_ms=now)
    return response

if result.outcome == Outcome.REPLAY_SUCCESS:
    return result.entry.response_body

if result.outcome == Outcome.CONFLICT:
    return 422   # key reused with different payload

if result.outcome == Outcome.IN_PROGRESS:
    return 409   # racing retry, ask client to back off
```

## Outcomes

| Outcome           | Meaning                                                |
| ----------------- | ------------------------------------------------------ |
| NEW               | No existing entry; just reserved as IN_PROGRESS        |
| REPLAY_SUCCESS    | Existing succeeded entry, same payload — return cached |
| REPLAY_FAILED     | Existing failed entry — caller decides whether to retry |
| IN_PROGRESS       | Existing reservation still mid-flight                  |
| CONFLICT          | Existing entry, different payload — likely client bug   |

## CLI

```bash
pip install idempotency-key-store

idemp fingerprint '{"op":"transfer","amount":100}'
# → {"payload": "...", "fingerprint": "abc123..."}

idemp simulate-run --unique 100 --total 1000 --ttl-ms 60000
# → {"n_requests": 1000, "outcomes": {"new": 100, "replay_success": 900, ...}}
```

## Caveats

* This is an **in-memory** reference store. Production needs Redis
  (`SET NX EX`), DynamoDB (with TTL attribute), or Postgres (with a
  uniqueness constraint on the key column).
* Fingerprinting uses raw `payload.encode("utf-8")`. For JSON
  payloads, canonicalise first (sorted keys, stripped whitespace)
  so semantically-equal payloads produce equal fingerprints.
* The TTL must be longer than the longest plausible client retry
  window — typically 24 hours.

## License

MIT.
