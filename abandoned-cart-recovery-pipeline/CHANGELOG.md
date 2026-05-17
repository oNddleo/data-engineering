# Changelog

## [0.1.0] — 2026-05-17

### Added
- `Event`, `Session`, `CampaignTouch` frozen-slots dataclasses with
  validation at construction (tz-aware datetimes, non-empty IDs,
  cart-mutating events require `item_id` + `unit_price_vnd`,
  non-negative cart values).
- `EventKind` enum with the canonical six funnel events: VIEW_ITEM,
  ADD_TO_CART, REMOVE_FROM_CART, START_CHECKOUT, COMPLETE_CHECKOUT,
  ABANDON_CHECKOUT.
- `sessionize(events, idle_gap_minutes=30)` — per-buyer single-pass
  fold with idle-gap session boundaries. Forces an explicit
  session boundary on `COMPLETE_CHECKOUT` / `ABANDON_CHECKOUT` —
  the buyer's next event opens a new session.
- `cart_value_vnd` clamped at zero — out-of-order webhook with
  REMOVE before ADD doesn't produce a negative cart.
- `find_abandoned(sessions, min_cart_vnd=50_000)` with three-way
  reason classification (`EXPLICIT`, `CHECKOUT_DROPOFF`,
  `IDLE_TIMEOUT`) and `abandon_rate` over carting sessions only.
- `schedule(abandoned, cadence=DEFAULT_CADENCE)` — VN-marketplace-
  standard 1h EMAIL → 24h SMS → 72h PUSH cadence with per-vertical
  override.
- `filter_due(touches, now)` — returns the subset of touches whose
  `scheduled_at <= now`, for the production fulfilment runner.
- `attribute(touches, events, attribution_window_hours=24)` —
  first-touch attribution by default, `last_touch=True` for the
  alternative. One conversion credits at most one touch per buyer.
- `conversion_rate`, `conversion_by_channel` for dashboard rollups.
- Seeded synthetic generator (`simulator.generate`) producing
  events across 5 buyer archetypes (window_shopper, cart_filler,
  checkout_dropoff, explicit_abandon, converter) with a configurable
  `recovery_fraction` that injects post-abandon conversions inside
  the attribution window — exercising the attribution-positive path.
- Type-checked JSONL codec with `_require_str` / `_require_int` /
  `_require_bool` / `_optional_*` decoders (rejects `bool` for `int`,
  string for `bool`, unknown enum values).
- CLI `cartrec info | simulate | sessionize | detect | schedule | attribute | summary`.
- 84 tests including 6 Hypothesis properties (sum of session
  `n_events` equals input length; `started_at <= ended_at` always;
  `cart_value_vnd` is always ≥ 0; abandon rate in [0, 1];
  abandoned sessions always have `n_add ≥ 1`; attribution is
  consistent with the window — converted iff conversion falls in
  `[touch_ts, touch_ts + window]`).
- mypy `--strict` clean over 9 source files; ruff clean.
- Multi-stage slim Docker image, non-root `cartrec` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- Zero runtime dependencies.

### Notes
- The first cut of the attribution tests created conversion events
  via `make_event` without overriding `buyer_id`, so the default
  `"B-0001"` mismatched the touch buyer `"B-1"`. Attribution
  correctly refused to credit cross-buyer matches; the tests were
  updated to set `buyer_id="B-1"` explicitly. This caught a real
  invariant: attribution **must be per-buyer**, never a cross-buyer
  match.
- `sessionize` reuses the same loop variable name (`group`) across
  two different dict views in `attribute.py`, which made mypy
  pessimistically widen the type. Renamed to `events_group` and
  `touches_group` to keep mypy happy without `cast`.
- The recovery-window simulator places synthesised conversions
  2-22h after the session ends — that's intentionally inside the
  email attribution window (24h) but **outside** the SMS window
  (which starts at 24h, ends at 48h). The smoke run shows 100% of
  attributed conversions going to EMAIL, which matches the
  positioning by design. Tune the simulator's recovery_offset to
  exercise other channels.
