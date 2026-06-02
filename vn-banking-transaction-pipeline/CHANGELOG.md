# Changelog

## 0.1.0 — 2026-05-19

Initial production-grade release.

* **Schema** — `Bank`, `Account`, `Transaction`, `DailySummary` with
  10-kind `TxnKind` (intra/interbank/VietQR send+receive/cash±/card/
  bill/salary/interest), 4-state `TxnStatus`, and direction-signed
  `signed_amount_vnd` helper.
* **Bank directory** — 18 VN commercial banks with NAPAS 6-digit
  BIN codes (Vietcombank, Techcombank, BIDV, VietinBank, Agribank,
  MB, VPBank, ACB, SHB, TPBank, Sacombank, Eximbank, HDBank, VIB,
  MSB, OCB, SeABank, VCCB). Account-number validation by per-bank
  length range.
* **VietQR codec** — EMV-spec TLV builder + parser with CRC-16/CCITT-
  FALSE verification. Supports static + dynamic QRs, purpose field
  in tag 62, NAPAS AID `A000000727` in tag 38, QRIBFTTA service code.
* **Routing** — NAPAS-247 vs Citad selection with 500M VND cap per
  SBV Decision 1085/QĐ-NHNN (2024-07-01); intra-bank fast path; 2025
  market-blended fee schedule.
* **Daily summary** — per-account, per-day rollups grouping by VN-local
  date; REVERSED counts in `n_txns` but excludes from totals; REJECTED
  excluded entirely.
* **AML signals** — `find_ctr` (≥300M VND cash flow/day per Decree
  87/2017), `find_structuring` (≥3 sub-CTR cash deposits summing to
  ≥CTR), `find_high_velocity` (sliding-window outbound-debit burst
  detector, default 50 txns/hour).
* **Simulator** — `generate(n_accounts, n_days, seed)` with
  configurable AML-positive cohorts (CTR / structuring / velocity
  fractions, all default 2%).
* **CLI** — `info | banks | qr | simulate | summary | aml | route`;
  `aml` exits 2 when any finding fires (CI-friendly).
* **JSONL codec** — round-trip for `Transaction`, `DailySummary`,
  `AMLFinding` with typed decoders.
* **Quality gate** — 117 tests with Hypothesis property tests;
  `mypy --strict` clean; ruff lint + format clean; zero runtime deps.
