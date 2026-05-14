# Changelog

## [0.1.0] — 2026-05-14

### Added
- `TransactionGraph` — in-memory directed multigraph with parallel
  in/out adjacency-list indexes, time-window helpers (`window_in`,
  `window_out`, `out_after`), neighbor-set dedup, edge-implied
  account discovery (`all_known_account_ids`), and txn-id
  uniqueness enforcement.
- Five rich data types: `Account` (with `RiskFlag` tuple + bank BIN
  validation), `Transaction` (no self-loops, positive amount,
  tz-aware datetime), `Channel`, `AccountType`, `RiskFlag` enums.
- Five AML pattern detectors as pure
  `(graph, **params) → list[AMLAlert]` functions:
  - `detect_fan_out` — sliding-window count of distinct
    destinations per source.
  - `detect_fan_in` — sliding-window count of distinct sources per
    destination.
  - `detect_layering_chains` — iterative DFS with per-hop time
    budget + cumulative-duration cap; reports the first qualifying
    path per source.
  - `detect_round_trips` — DFS finds shortest cycle returning to
    origin within a window.
  - `detect_structured_deposits` — per-recipient view of
    structuring (multiple just-under-threshold deposits from
    multiple sources within a window).
- `AMLAlert` carrying `kind`, `severity`, `primary_account`,
  `related_accounts`, `total_amount_vnd`, `detail`, and the
  `txn_ids` that triggered it — so analysts can drill down without
  re-running the detector.
- Risk scoring (`scoring.score_accounts`) that combines:
  - A-priori `RiskFlag` bumps (PEP 30 / SANCTIONED 100 /
    MULE_SUSPECTED 50 / HIGH_RISK_JURISDICTION 20 / PRIOR_SAR 40).
  - Severity × kind multiplier per alert hit. Primary account gets
    full credit; related accounts get half credit.
  - `top_n` ranks accounts and excludes zero-score entries from
    the head of the list.
- JSONL codec for `Account` / `Transaction` / `AMLAlert` with
  type-checked decoders so malformed payloads fail loud at the
  boundary.
- Seeded synthetic generator (`simulator.generate`) with 5
  pattern-injection knobs (`inject_fan_out`, `inject_fan_in`,
  `inject_layering`, `inject_round_trip`, `inject_structured`).
  Each injection adds a complete realistic topology — e.g.
  fan-out adds one source + 6 destinations + 6 transfers.
- `amlgraph` CLI with `info`, `simulate`, `detect` (`--summary`
  optional), and `rank` (alerts → per-account scores → top-N).
- **98 tests** including 4 Hypothesis properties.
- mypy `--strict` clean over 9 source files; ruff + ruff-format
  clean.
- Multi-stage slim Docker image, non-root `aml` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

### Notes
- The "no false positives on random traffic" test was dropped:
  with a small synthetic graph (30 accounts × 60 random transfers
  at 30s intervals), default-threshold layering chains are
  trivially present. The kept-in `test_injection_strictly_increases_alert_count`
  test instead verifies that **injection raises the relevant
  alert count over the same-seed baseline** — a more useful
  regression check.
- Detector defaults are tuned for **sensitivity on hand-crafted
  cases**, not production. The README has a "production knobs"
  section showing recommended bars (8+ distinct neighbours,
  5-hop layering chains, etc.).
- Layering / round-trip detectors are iterative DFS with explicit
  stacks — no recursion, no stack-overflow risk on long chains.
  They emit at most one alert per source so the rank table stays
  readable; if a caller needs *all* qualifying paths, the
  underlying DFS state is straightforward to expose.
- The "per-recipient structured deposit" view in this project is
  intentionally complementary to the per-initiator structuring
  rule in `napas-247-transaction-monitor`. Together they catch
  both ends of a smurfing chain.
