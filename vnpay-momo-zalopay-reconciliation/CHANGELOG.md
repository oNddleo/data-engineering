# Changelog

## [0.1.0] — 2026-05-14

### Added
- `WalletTxn` / `MerchantOrder` dataclasses with frozen, slot-backed
  invariants (non-negative VND amounts, non-empty IDs, tz-aware
  datetimes).
- Wallet-code → canonical `Status` mappers for the three wallets:
  VNPay (`vnp_ResponseCode` string), MoMo (`resultCode` int with
  9000 alias for "captured later" and 1000–1006 / 7000–7002 pending
  range), ZaloPay (`status` int with 3 as pending).
- Amount + timestamp converters: `vnpay_amount_to_vnd` (VND × 100 →
  raw VND, rejects non-divisible-by-100 inputs), `vnpay_paydate_to_datetime`
  (`yyyyMMddHHmmss` local → UTC+7), `epoch_ms_to_datetime` (UTC
  epoch ms → UTC+7).
- Four CSV parsers (`parse_vnpay_csv`, `parse_momo_csv`,
  `parse_zalopay_csv`, `parse_merchant_csv`) with a single
  `ParseError` exception carrying `file_kind`, 1-indexed
  `row_number`, `field`, and `message` — so a failed row can be
  grepped in the original spreadsheet immediately.
- 3-way `reconcile` core with five discrepancy kinds: `WALLET_ONLY`,
  `MERCHANT_ONLY`, `AMOUNT_MISMATCH`, `STATUS_MISMATCH`,
  `DUPLICATE_IN_WALLET`. Sorted output for stable day-over-day diff.
- Suppression rules: PENDING on either side mutes status mismatch;
  AMOUNT_MISMATCH preempts STATUS_MISMATCH; MERCHANT_ONLY only fires
  when merchant claimed SUCCESS.
- Text / CSV / JSON report formatters + `summarise` with
  `net_vnd_missing` aggregate.
- `vmzrecon` CLI with `info`, `parse --wallet {vnpay,momo,zalopay,merchant}`,
  `reconcile --merchant ... --vnpay ... --momo ... --zalopay ... --format {text,csv,json}`.
- **83 tests** including 5 Hypothesis property tests:
  perfect-mirror invariant, wallet-only count invariant, summarise
  total invariant, VNPay status mapper totality, MoMo status mapper
  totality.
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `vmz` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

### Notes
- `WALLET_ONLY` discrepancy detail strings format VND amounts with
  thousands separators (`100,000 VND` not `100000`), since the daily
  Slack report is read by humans first.
- Cross-wallet same-order-id is explicitly tested — ORD-1 on VNPay
  and ORD-1 on MoMo must be independent reconciliation keys.
- The Python 3.13 anaconda interpreter used for local development
  emits a `hatchling` editable-install warning when `README.md` is
  missing; the README is created before any wheel build to avoid
  this.
