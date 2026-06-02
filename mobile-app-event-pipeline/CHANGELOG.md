# Changelog

## [0.1.0] — 2026-05-18

### Added
- `Event`, `EventKind` (CLICK / IMPRESSION / INSTALL / OPEN / IN_APP /
  PURCHASE), `Attribution`, `CohortRetention`, `CohortLTV`
  frozen-slots dataclasses with validation at construction (tz-aware
  `occurred_at`, non-negative `revenue_vnd`, `IN_APP` requires
  `in_app_event_name`, `revenue_vnd` must be 0 for non-`PURCHASE`).
- `VN_TZ = UTC+7` for VN-local install-date cohorting.
- `mappev.attribute.attribute()` — last-touch attribution with
  configurable click-window (default 7d) and view-window (default
  24h). Matches Appsflyer ordering: last qualifying click → last
  qualifying impression → organic. Ties broken on lexicographic
  `event_id`. Output sorted by `(install_at, device_id)`.
- `mappev.cohort.retention()` — D1 / D7 / D30 retention curves per
  VN_TZ install-date cohort. "Active" = at least one
  `OPEN`/`IN_APP`/`PURCHASE` event in the disjoint 24-hour window
  `[install + N days, install + (N+1) days)`.
- `mappev.cohort.ltv()` — cumulative LTV per cohort at D1 / D7 / D30
  horizons (`revenue_d1 ≤ revenue_d7 ≤ revenue_d30`). Per-device
  average is `revenue // cohort_size` (integer-VND).
- `mappev.fraud.find_click_injection()` — surfaces (source, campaign)
  pairs with ≥ 3 installs attributed at lag < 20s (Adjust's
  published click-injection threshold). Configurable threshold.
- `mappev.fraud.find_install_spam()` — surfaces sources with
  ≥ `min_installs` (default 10) and D1 retention < `min_d1_rate_pct`
  (default 5%). Detects device-farm operators selling installs
  that never open the app.
- `mappev.simulator.generate()` — seeded synthetic event stream
  with five device populations: organic (35%), click-attributed
  (45%), view-attributed (10%), click-injection (5%), install-spam
  (5%). Realistic VN source/campaign pairs (facebook, google_ads,
  tiktok, zalo).
- `mappev.io_jsonl` — type-checked JSONL codec for events,
  attributions, cohort retention, cohort LTV, and fraud findings.
  Rejects bool-as-int (`revenue_vnd: true`) and wrong-type fields.
- `mappev.cli` — `mappev info | simulate | attribute | cohort |
  ltv | fraud | summary`. `fraud` exits **2** when any finding is
  surfaced (CI-gate compatible).
- 94 unit tests + 11 Hypothesis properties; mypy `--strict` clean;
  ruff clean; multi-stage slim Docker image.

[0.1.0]: https://github.com/sophie-nguyenthuthuy/data-engineering/releases/tag/mobile-app-event-pipeline-v0.1.0
