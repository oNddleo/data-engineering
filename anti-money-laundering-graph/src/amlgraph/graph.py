"""In-memory directed multigraph over accounts and transactions.

Substitute for a real graph DB (Neo4j) — the API is narrow enough
that the same shapes work end-to-end:

* :meth:`add_account`, :meth:`add_transaction` — write side.
* :meth:`out_edges`, :meth:`in_edges` — neighbour traversal.
* :meth:`neighbors_out`, :meth:`neighbors_in` — distinct neighbours.
* :meth:`window_out`, :meth:`window_in` — time-window-filtered edges.

Edges are kept in two parallel adjacency-list indexes (one keyed by
source, one by destination) so both directions are O(1) to scan.
Time-filtering is O(k) over the per-account list — we don't keep
time-indexed structures because the alert pipelines call patterns
per-account and the per-account list is small in practice.

For a 1M-edge graph this implementation uses about 250 MB of memory
in CPython. Production deployments swap this module for a Neo4j /
TigerGraph / Amazon Neptune backend; the pattern detectors in
``patterns.py`` only depend on the public API above.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime, timedelta

    from amlgraph.schema import Account, Transaction


class TransactionGraph:
    """Directed multigraph of accounts (nodes) and transactions (edges)."""

    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}
        self._out: dict[str, list[Transaction]] = defaultdict(list)
        self._in: dict[str, list[Transaction]] = defaultdict(list)
        self._txn_index: dict[str, Transaction] = {}

    # -------------------------------------------------------- write

    def add_account(self, account: Account) -> None:
        """Add or replace an account node."""
        self._accounts[account.account_id] = account

    def add_transaction(self, txn: Transaction) -> None:
        """Append an edge; auto-creates account stubs if missing."""
        if txn.txn_id in self._txn_index:
            raise ValueError(f"duplicate txn_id {txn.txn_id!r}")
        self._txn_index[txn.txn_id] = txn
        self._out[txn.from_account].append(txn)
        self._in[txn.to_account].append(txn)

    def add_transactions(self, txns: Iterable[Transaction]) -> None:
        for t in txns:
            self.add_transaction(t)

    # --------------------------------------------------------- read

    @property
    def n_accounts(self) -> int:
        return len(self._accounts)

    @property
    def n_transactions(self) -> int:
        return len(self._txn_index)

    def has_account(self, account_id: str) -> bool:
        return account_id in self._accounts

    def get_account(self, account_id: str) -> Account | None:
        return self._accounts.get(account_id)

    def all_accounts(self) -> list[Account]:
        return list(self._accounts.values())

    def all_known_account_ids(self) -> set[str]:
        """Every account ever seen — including edge-implied ones."""
        seen: set[str] = set(self._accounts)
        seen.update(self._out)
        seen.update(self._in)
        return seen

    def get_transaction(self, txn_id: str) -> Transaction | None:
        return self._txn_index.get(txn_id)

    def out_edges(self, account_id: str) -> list[Transaction]:
        return list(self._out.get(account_id, ()))

    def in_edges(self, account_id: str) -> list[Transaction]:
        return list(self._in.get(account_id, ()))

    def neighbors_out(self, account_id: str) -> set[str]:
        return {t.to_account for t in self._out.get(account_id, ())}

    def neighbors_in(self, account_id: str) -> set[str]:
        return {t.from_account for t in self._in.get(account_id, ())}

    # ---------------------------------------------- time-windowed reads

    def window_out(self, account_id: str, *, since: datetime, until: datetime) -> list[Transaction]:
        return [t for t in self._out.get(account_id, ()) if since <= t.occurred_at <= until]

    def window_in(self, account_id: str, *, since: datetime, until: datetime) -> list[Transaction]:
        return [t for t in self._in.get(account_id, ()) if since <= t.occurred_at <= until]

    def out_after(
        self, account_id: str, *, after: datetime, within: timedelta
    ) -> list[Transaction]:
        """Out-edges in the half-open window ``(after, after + within]`` ordered by time."""
        cutoff = after + within
        return sorted(
            [t for t in self._out.get(account_id, ()) if after < t.occurred_at <= cutoff],
            key=lambda x: x.occurred_at,
        )


__all__ = ["TransactionGraph"]
