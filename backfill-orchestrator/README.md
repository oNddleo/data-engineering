# backfill-orchestrator

Time-partition backfill orchestrator.
Splits a date range into partitions, tracks state (PENDING/RUNNING/DONE/FAILED),
enforces max-concurrency, supports priority ordering, and can checkpoint
and resume from JSONL state files.

## License
MIT
