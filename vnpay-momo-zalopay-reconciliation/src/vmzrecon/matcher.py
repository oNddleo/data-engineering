"""Three-way reconciliation core.

Inputs: any iterable of :class:`MerchantOrder` (the source of truth
for "what the merchant expects to be paid for") plus any iterable of
:class:`WalletTxn` (what each wallet actually settled today).

Output: a deterministic, sorted list of :class:`Discrepancy` records.

Matching rules:

1. Wallet txns are keyed on ``(wallet, merchant_order_id)``. If the
   same key appears twice we emit one ``DUPLICATE_IN_WALLET``
   discrepancy and use the *first* occurrence for further checks —
   the second is suppressed to avoid double-counting amount and
   status mismatches that would just be artefacts of the duplicate.
2. Merchant orders are also keyed on ``(wallet, order_id)``. We
   assume merchant ledgers are unique per (wallet, order_id) — if
   not, the loader should dedupe before calling us.
3. For each key in the union of both sides:

   * Wallet-only → ``WALLET_ONLY``.
   * Merchant-only **with merchant status SUCCESS** → ``MERCHANT_ONLY``
     (money not received). Merchant FAILED/PENDING that has no wallet
     row is *not* a discrepancy — it never claimed money was moved.
   * Both present:

     * Amount differs → ``AMOUNT_MISMATCH`` (and we stop further
       comparison on this key — the row is already broken).
     * Else if status differs → ``STATUS_MISMATCH``. We compare only
       SUCCESS vs FAILED here; if either side is PENDING we suppress
       the mismatch because settlement is still in flight and the
       row will reappear in tomorrow's file.

Output ordering: by ``(wallet, order_id, kind)`` ascending. Stable
ordering matters because daily diff reports are often diffed against
yesterday's report by ops.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vmzrecon.discrepancy import Discrepancy, DiscrepancyKind
from vmzrecon.schema import Status, Wallet

if TYPE_CHECKING:
    from collections.abc import Iterable

    from vmzrecon.schema import MerchantOrder, WalletTxn

_Key = tuple[Wallet, str]


def _index_wallet_txns(
    txns: Iterable[WalletTxn],
) -> tuple[dict[_Key, WalletTxn], list[Discrepancy]]:
    """Build a (wallet, order_id) → first-txn index and collect duplicates."""
    first_seen: dict[_Key, WalletTxn] = {}
    seen_count: dict[_Key, int] = {}
    duplicates: list[Discrepancy] = []
    for t in txns:
        key = (t.wallet, t.merchant_order_id)
        if key in first_seen:
            seen_count[key] = seen_count.get(key, 1) + 1
        else:
            first_seen[key] = t
            seen_count[key] = 1
    for key, count in seen_count.items():
        if count > 1:
            wallet, order_id = key
            duplicates.append(
                Discrepancy(
                    kind=DiscrepancyKind.DUPLICATE_IN_WALLET,
                    wallet=wallet,
                    order_id=order_id,
                    detail=f"order_id appears {count} times in {wallet.value} settlement file",
                )
            )
    return first_seen, duplicates


def _index_merchant(orders: Iterable[MerchantOrder]) -> dict[_Key, MerchantOrder]:
    return {(o.wallet, o.order_id): o for o in orders}


def _compare_pair(
    key: _Key, wallet_txn: WalletTxn, merchant_order: MerchantOrder
) -> Discrepancy | None:
    wallet, order_id = key
    if wallet_txn.amount_vnd != merchant_order.expected_amount_vnd:
        return Discrepancy(
            kind=DiscrepancyKind.AMOUNT_MISMATCH,
            wallet=wallet,
            order_id=order_id,
            detail=(
                f"merchant expected {merchant_order.expected_amount_vnd:,} VND, "
                f"wallet settled {wallet_txn.amount_vnd:,} VND"
            ),
            wallet_amount=wallet_txn.amount_vnd,
            merchant_amount=merchant_order.expected_amount_vnd,
        )
    if Status.PENDING in (wallet_txn.status, merchant_order.status):
        # Settlement still in flight on at least one side — suppress.
        return None
    if wallet_txn.status != merchant_order.status:
        return Discrepancy(
            kind=DiscrepancyKind.STATUS_MISMATCH,
            wallet=wallet,
            order_id=order_id,
            detail=(
                f"merchant status={merchant_order.status.value}, "
                f"wallet status={wallet_txn.status.value} "
                f"(wallet code={wallet_txn.raw_response_code!r})"
            ),
            wallet_amount=wallet_txn.amount_vnd,
            merchant_amount=merchant_order.expected_amount_vnd,
        )
    return None


def reconcile(
    merchant_orders: Iterable[MerchantOrder],
    wallet_txns: Iterable[WalletTxn],
) -> list[Discrepancy]:
    """Run a 3-way reconciliation pass.

    Returns a sorted list of discrepancies. An empty list means the
    inputs match perfectly.
    """
    wallet_idx, discrepancies = _index_wallet_txns(wallet_txns)
    merchant_idx = _index_merchant(merchant_orders)

    all_keys = set(wallet_idx) | set(merchant_idx)
    for key in all_keys:
        wallet, order_id = key
        wallet_txn = wallet_idx.get(key)
        merchant_order = merchant_idx.get(key)

        if wallet_txn is not None and merchant_order is None:
            discrepancies.append(
                Discrepancy(
                    kind=DiscrepancyKind.WALLET_ONLY,
                    wallet=wallet,
                    order_id=order_id,
                    detail=(
                        f"{wallet.value} settled {wallet_txn.amount_vnd:,} VND "
                        f"but no matching merchant order"
                    ),
                    wallet_amount=wallet_txn.amount_vnd,
                )
            )
            continue
        if wallet_txn is None and merchant_order is not None:
            if merchant_order.status is Status.SUCCESS:
                discrepancies.append(
                    Discrepancy(
                        kind=DiscrepancyKind.MERCHANT_ONLY,
                        wallet=wallet,
                        order_id=order_id,
                        detail=(
                            f"merchant marked SUCCESS for {merchant_order.expected_amount_vnd:,} VND "
                            f"via {wallet.value} but settlement file does not contain it"
                        ),
                        merchant_amount=merchant_order.expected_amount_vnd,
                    )
                )
            continue
        if wallet_txn is not None and merchant_order is not None:
            pair_disc = _compare_pair(key, wallet_txn, merchant_order)
            if pair_disc is not None:
                discrepancies.append(pair_disc)

    discrepancies.sort(key=lambda d: (d.wallet.value, d.order_id, d.kind.value))
    return discrepancies


__all__ = ["reconcile"]
