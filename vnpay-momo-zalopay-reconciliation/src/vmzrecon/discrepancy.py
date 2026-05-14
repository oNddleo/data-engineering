"""Discrepancy types produced by the reconciler.

A discrepancy is anything the merchant ops team has to look at by
hand. We deliberately distinguish five kinds so the daily report can
be routed to different teams:

* :attr:`DiscrepancyKind.WALLET_ONLY` — the wallet settled a
  transaction with a merchant order id that doesn't exist in the
  merchant's ledger. Usually a partner-integration bug or fraud
  signal; goes to security.
* :attr:`DiscrepancyKind.MERCHANT_ONLY` — the merchant marked an
  order as paid through this wallet, but the wallet's settlement
  file doesn't list it. *Money not yet received.* Goes to finance.
* :attr:`DiscrepancyKind.AMOUNT_MISMATCH` — both sides agree the
  transaction happened but disagree on the amount. Goes to finance.
* :attr:`DiscrepancyKind.STATUS_MISMATCH` — both sides agree on
  amount + order id but disagree on terminal status (merchant says
  SUCCESS, wallet says FAILED, or vice versa). Goes to merchant ops.
* :attr:`DiscrepancyKind.DUPLICATE_IN_WALLET` — the wallet's
  settlement file contains the same ``merchant_order_id`` twice,
  which should never happen. Goes to the wallet partner team.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vmzrecon.schema import Wallet


class DiscrepancyKind(str, Enum):
    """Kinds of recon discrepancy."""

    WALLET_ONLY = "WALLET_ONLY"
    MERCHANT_ONLY = "MERCHANT_ONLY"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    STATUS_MISMATCH = "STATUS_MISMATCH"
    DUPLICATE_IN_WALLET = "DUPLICATE_IN_WALLET"


@dataclass(frozen=True, slots=True)
class Discrepancy:
    """A single unmatched / mismatched record between merchant + wallet."""

    kind: DiscrepancyKind
    wallet: Wallet
    order_id: str
    detail: str
    wallet_amount: int | None = None
    merchant_amount: int | None = None


__all__ = ["Discrepancy", "DiscrepancyKind"]
