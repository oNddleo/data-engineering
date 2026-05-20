# Changelog

## 0.1.0 — 2026-05-20

Initial production-grade release.

* **Schema** — `Window` (half-open interval), `Event`, `WindowedAggregate`
  with per-(window, key) count/sum/min/max + computed avg.
* **Tumbling** — `assign_window(ts, width)` + `aggregate(events, width)`.
* **Sliding** — `windows_for(ts, width, stride)` returns every window
  containing the event; `aggregate(events, width, stride)` rolls up.
* **Session** — gap-based per-key sessionisation; events within
  `timeout_ms` belong to the same session.
* **Simulator** — uniform + bursty event-stream generators.
* **CLI** — `info | simulate | tumbling | sliding | session | summary`.
* **JSONL codec** — round-trip for `Event` and `WindowedAggregate`.
* **Quality gate** — 75 tests with Hypothesis property tests
  (count/sum conservation, sliding-window stride alignment,
  sliding-stride-equal-width reduces to tumbling, JSONL round-trip);
  `mypy --strict` clean; ruff lint + format clean; zero runtime deps.
