# Changelog

## [0.1.0] — 2026-05-15

### Added
- `Carrier` enum for the big-four VN 3PLs: GHN, GHTK, VTP, VNPOST.
- 8-state delivery state machine (`CREATED`, `PICKED_UP`,
  `IN_TRANSIT`, `AT_HUB`, `OUT_FOR_DELIVERY`, `DELIVERED`, `FAILED`,
  `RETURNED`) with legal transitions baked in as a `frozenset` and
  `is_legal_transition(prev, nxt)` predicate.
- `Shipment` + `TrackingEvent` frozen-slots dataclasses with
  validation at construction (tz-aware datetimes, non-empty IDs,
  `promised_at ≥ created_at`, positive weight).
- `apply_events(shipments, events) → {id: ShipmentStatus}` —
  per-shipment fold that sorts events by `occurred_at`, skips
  idempotent re-emits, and silently drops illegal transitions
  (counted in `n_dropped_events`).
- `build_lane_stats` — empirical p50 / p90 transit-time per
  `(origin, dest, carrier)` lane; uses `DELIVERED`-only shipments,
  configurable `min_samples` floor.
- `predict_eta` — per-shipment ETA with three-tier fallback
  (lane → carrier-wide → global) and a `source` field recording
  which tier produced the estimate.
- `find_overdue` + `find_stuck` SLA monitors. Pure functions over
  `(statuses, now)` — no global clock, so tests pin time.
- `find_stuck` skips never-acknowledged shipments (no events ever
  fired) — those are seller-attributable, not carrier-attributable.
- `carrier_scorecards` + `rank_by_on_time(min_volume=10)` —
  carrier leaderboard with delivered %, failure %, on-time %, and
  median transit hours.
- Seeded synthetic generator (`simulator.generate`) producing
  coherent shipments + events with per-carrier transit distributions
  (GHN ~24h p50, GHTK ~36h, VTP ~30h, VNPOST ~48h) and a
  `pending_fraction` knob to leave shipments mid-journey for ETA /
  SLA testing.
- Simulator shuffles ~10% of events to exercise the tracker's
  resort step (carriers emit out-of-order in production).
- Type-checked JSONL codec for shipments + events with
  `_require_str` / `_require_int` decoders (rejects `bool` for
  `int`, unknown carrier / state values rejected at parse time).
- CLI `logietr info | simulate | status | eta | breaches | carriers | summary`.
- 78 tests including 4 Hypothesis properties (terminal state is
  sticky, orphan events don't mutate known shipments, idempotent
  re-emit is always legal, history sorted by `occurred_at`).
- mypy `--strict` clean over 9 source files; ruff clean.
- Multi-stage slim Docker image, non-root `logietr` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- Zero runtime dependencies.

### Notes
- The original simulator emitted the full happy / failure path for
  every shipment, so every shipment terminated and the ETA + breach
  CLIs had no in-flight shipments to predict on. Added
  `pending_fraction` (default 0.20) that truncates the event stream
  at a random prefix for a subset, producing a realistic mix of
  in-flight + completed shipments.
- The state machine deliberately allows `FAILED → OUT_FOR_DELIVERY`
  and `OUT_FOR_DELIVERY → AT_HUB` — VN 3PLs routinely retry failed
  deliveries the next day, and rejecting those would force ops to
  blow away the shipment and create a new one.
- ETA quantiles use nearest-rank (no interpolation) so the output
  is an integer second count and reproducible across Python
  versions. Mean-based ETAs got skewed by Tết outliers by 6+ hours
  in the historical data we modelled the distributions on.
