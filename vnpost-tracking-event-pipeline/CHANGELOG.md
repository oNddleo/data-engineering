# Changelog

## [0.1.0] — 2026-05-19

### Added
- `ParcelEventKind` enum with 8 scan kinds (CREATED / PICKED_UP /
  IN_TRANSIT / AT_HUB / OUT_FOR_DELIVERY / DELIVERED /
  RETURN_TO_SENDER / EXCEPTION).
- `ParcelStatus` enum with 6 status values (PENDING / IN_FLIGHT /
  DELIVERED / RETURNED / LOST / EXCEPTION).
- `CourierCode` enum covering 5 VN majors (VTP / GHN / GHTK / JT /
  SPX) — ~85% of the e-commerce parcel volume.
- `ParcelEvent`, `Parcel`, `CourierSLA` frozen-slots dataclasses
  with validation at construction (non-empty IDs, tz-aware
  datetimes, consistent count fields).
- `vnpost.hubs` — bundled 16-hub directory across HCM (5) / HN (4) /
  DN (2) / HP (2) / CT (2) plus the national sortation centre.
  `all_hubs()`, `by_code()`, `by_city()`, `gateways()`.
- `vnpost.couriers` — bundled 5-courier directory with per-courier
  SLA targets (same-city 24-36h, inter-city 72-120h).
  `profile()` + `sla_hours()`.
- `vnpost.state` — state-machine validator + `stitch()` event
  stream into Parcel rows. Same-city legal shortcut
  (PICKED_UP → OUT_FOR_DELIVERY) supported.
- `vnpost.sla.compute_sla()` — per-courier on-time rate +
  median / p95 transit hours. `tet_aware=True` subtracts the 5-day
  Tết block (giao thừa through Mùng 4) from transit time before
  comparing to SLA. Tết dates hard-coded for 2024-2027.
- `vnpost.sla.hours_in_tet_block()` — overlap of an interval with
  any of the bundled Tết blocks.
- `vnpost.fraud.find_scan_skipping()` — flags DELIVERED parcels
  with < 4 scans for inter-city journeys (< 3 for same-city).
- `vnpost.fraud.find_abnormal_dwell()` — flags inter-hub dwells
  that exceed p95 + ``iqr_multiplier × (p95 - p50)`` across the
  population.
- `vnpost.simulator.generate()` — seeded synthetic event streams
  with 6 outcome types: delivered normally / late / returned /
  scan-skipping / abnormal-dwell / exception.
- `vnpost.io_jsonl` — type-checked JSONL codec for events,
  parcels, SLAs, fraud findings.
- `vnpost.cli` — `vnpost info | simulate | stitch | sla | fraud |
  summary`. `fraud` exits **2** on any finding.
- 84 unit tests + 7 Hypothesis properties; mypy `--strict` clean;
  ruff clean; multi-stage slim Docker image.

[0.1.0]: https://github.com/sophie-nguyenthuthuy/data-engineering/releases/tag/vnpost-tracking-event-pipeline-v0.1.0
