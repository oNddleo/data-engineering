# circuit-breaker-toolkit

Circuit breaker resilience pattern implementation (Fowler / Nygaard).
States: CLOSED (normal) → OPEN (failing, reject calls) → HALF_OPEN (probe).
Configurable failure threshold, reset timeout, and success threshold.
Thread-safe state machine with JSONL event logging.

## License
MIT
