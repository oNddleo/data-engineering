# vnpay-momo-zalopay-reconciliation

Đối soát giao dịch hàng ngày giữa **VNPay**, **MoMo**, **ZaloPay** và
sổ đơn hàng (merchant ledger) — sinh báo cáo chênh lệch theo chuẩn
NAPAS-normalised.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

Mỗi ngày, các ví VNPay / MoMo / ZaloPay gửi cho merchant một file CSV
settlement. Mỗi ví dùng schema riêng (cột khác nhau, encode amount /
status / timestamp khác nhau). Engine này:

1. **Parse** từng file theo schema của ví, normalise về một shape
   chung (`WalletTxn` — amount integer VND, status SUCCESS/FAILED/
   PENDING, datetime timezone-aware UTC+7).
2. **Match** với merchant order ledger 3 chiều
   (wallet ↔ order_id ↔ amount/status).
3. **Phát hiện** 5 loại chênh lệch:
   - `WALLET_ONLY` — ví settled nhưng merchant không có order
     (potential fraud / partner-integration bug).
   - `MERCHANT_ONLY` — merchant đã đánh dấu PAID nhưng ví không
     trả về (tiền chưa về tài khoản).
   - `AMOUNT_MISMATCH` — hai bên agree về tồn tại txn nhưng amount lệch.
   - `STATUS_MISMATCH` — agree về amount nhưng terminal status lệch.
   - `DUPLICATE_IN_WALLET` — cùng `merchant_order_id` xuất hiện 2 lần
     trong file ví (lỗi của partner).
4. **Output** report dạng text (Slack daily), CSV (đính kèm ticket),
   hoặc JSON (ship lên data warehouse).

PENDING ở bất kỳ bên nào → suppress mismatch, vì settlement chưa
hoàn thành. Row sẽ xuất hiện lại trong file ngày mai.

## Wallet code reference

| Wallet  | Success code      | Pending range                       | Amount encoding | Timestamp                |
| ------- | ----------------- | ----------------------------------- | --------------- | ------------------------ |
| VNPay   | `vnp_ResponseCode="00"` | `"07"` (under bank review)    | VND × 100       | `yyyyMMddHHmmss` (local) |
| MoMo    | `resultCode=0` or `9000` | `1000`–`1006`, `7000`–`7002`  | raw VND         | epoch milliseconds (UTC) |
| ZaloPay | `status=1`        | `status=3`                          | raw VND         | epoch milliseconds (UTC) |

Tham khảo: VNPay IPN docs (sandbox.vnpayment.vn), MoMo Open Platform
docs (developers.momo.vn), ZaloPay Open Platform docs.

## Components

| Module                 | Role                                                                  |
| ---------------------- | --------------------------------------------------------------------- |
| `vmzrecon.schema`      | `Wallet`, `Status`, `WalletTxn`, `MerchantOrder` + invariants         |
| `vmzrecon.normalize`   | wallet-code → canonical `Status`, amount + timestamp converters       |
| `vmzrecon.parsers`     | `parse_vnpay_csv`, `parse_momo_csv`, `parse_zalopay_csv`, `parse_merchant_csv` |
| `vmzrecon.discrepancy` | `DiscrepancyKind`, `Discrepancy`                                       |
| `vmzrecon.matcher`     | `reconcile(merchant_orders, wallet_txns) → list[Discrepancy]`         |
| `vmzrecon.report`      | text / CSV / JSON formatters + `summarise`                            |
| `vmzrecon.cli`         | `vmzrecon info | parse | reconcile`                                   |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
vmzrecon info

# Parse + dump one wallet's settlement file (smoke test the parser).
vmzrecon parse --wallet vnpay   --file vnpay-2026-05-14.csv
vmzrecon parse --wallet momo    --file momo-2026-05-14.csv
vmzrecon parse --wallet zalopay --file zalopay-2026-05-14.csv

# Daily 3-way recon.
vmzrecon reconcile \
  --merchant merchant-orders-2026-05-14.csv \
  --vnpay    vnpay-settlement-2026-05-14.csv \
  --momo     momo-settlement-2026-05-14.csv \
  --zalopay  zalopay-settlement-2026-05-14.csv \
  --format   text
```

Sample text output:

```
=== Daily Wallet Reconciliation ===
total discrepancies: 3
net VND missing (merchant - wallet): 150,000

by kind:
  WALLET_ONLY                 1
  MERCHANT_ONLY               1
  AMOUNT_MISMATCH             1
  STATUS_MISMATCH             0
  DUPLICATE_IN_WALLET         0

by wallet:
  VNPAY           1
  MOMO            1
  ZALOPAY         1

details:
  [WALLET_ONLY]      VNPAY   ORD-1: VNPAY settled 100,000 VND but no matching merchant order
  [MERCHANT_ONLY]    MOMO    ORD-2: merchant marked SUCCESS for 250,000 VND via MOMO ...
  [AMOUNT_MISMATCH]  ZALOPAY ORD-3: merchant expected 500,000 VND, wallet settled 499,000 VND
```

`--format csv` and `--format json` produce ticket-attachable /
warehouse-shippable variants.

## Library

```python
from vmzrecon import (
    parse_vnpay_csv, parse_momo_csv, parse_zalopay_csv, parse_merchant_csv,
    reconcile, format_text_report,
)

wallet_txns = (
    parse_vnpay_csv(open("vnpay.csv").read())
    + parse_momo_csv(open("momo.csv").read())
    + parse_zalopay_csv(open("zalopay.csv").read())
)
merchant_orders = parse_merchant_csv(open("merchant.csv").read())

for d in reconcile(merchant_orders, wallet_txns):
    print(d.kind.value, d.wallet.value, d.order_id, d.detail)

print(format_text_report(reconcile(merchant_orders, wallet_txns)))
```

## Matching rules

1. Keys are `(wallet, merchant_order_id)`. Same order_id under
   different wallets → independent keys.
2. Duplicates in a wallet file → one `DUPLICATE_IN_WALLET` per
   duplicated key; the *first* occurrence is used for further
   comparisons (avoids double-counting amount/status mismatches that
   are artefacts of the duplicate).
3. `MERCHANT_ONLY` is reported **only** when the merchant order is
   marked SUCCESS — a FAILED/PENDING merchant order with no wallet
   row is not a discrepancy (no money was claimed to have moved).
4. `AMOUNT_MISMATCH` preempts `STATUS_MISMATCH` — if amounts differ
   we don't bother emitting status as well, the row is already broken.
5. PENDING on either side suppresses status mismatch — settlement
   in flight.
6. Output is sorted by `(wallet, order_id, kind)` so daily diff vs
   yesterday's report is deterministic.

## Quality

```bash
make test       # 83 tests, hypothesis property tests included
make type       # mypy --strict
make lint
```

- **83 tests** including 5 Hypothesis properties (identical-side
  invariant, wallet-only count invariant, summarise total invariant,
  + status mapper totality for VNPay/MoMo).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `vmz` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
