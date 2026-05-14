"""TransactionGraph tests."""

from __future__ import annotations

from datetime import timedelta

import pytest

from amlgraph.graph import TransactionGraph

from ._fixtures import make_account, make_txn, t_at


def test_empty_graph():
    g = TransactionGraph()
    assert g.n_accounts == 0
    assert g.n_transactions == 0


def test_add_account_idempotent_replace():
    g = TransactionGraph()
    g.add_account(make_account(account_id="A"))
    g.add_account(make_account(account_id="A"))  # replaces
    assert g.n_accounts == 1


def test_add_transaction_indexes_both_directions():
    g = TransactionGraph()
    g.add_transaction(make_txn(txn_id="T-1", src="A", dst="B"))
    assert {t.txn_id for t in g.out_edges("A")} == {"T-1"}
    assert {t.txn_id for t in g.in_edges("B")} == {"T-1"}
    assert g.neighbors_out("A") == {"B"}
    assert g.neighbors_in("B") == {"A"}


def test_add_transaction_rejects_duplicate_id():
    g = TransactionGraph()
    g.add_transaction(make_txn(txn_id="T-1", src="A", dst="B"))
    with pytest.raises(ValueError):
        g.add_transaction(make_txn(txn_id="T-1", src="A", dst="C"))


def test_add_transactions_bulk():
    g = TransactionGraph()
    g.add_transactions(
        [make_txn(txn_id=f"T-{i}", src="A", dst=f"B{i}", occurred_at=t_at(i)) for i in range(5)]
    )
    assert g.n_transactions == 5


def test_all_known_account_ids_includes_edge_implied():
    g = TransactionGraph()
    g.add_transaction(make_txn(src="X", dst="Y"))
    # No explicit add_account calls — graph should still know X and Y.
    assert "X" in g.all_known_account_ids()
    assert "Y" in g.all_known_account_ids()


def test_get_transaction():
    g = TransactionGraph()
    t = make_txn(txn_id="T-42")
    g.add_transaction(t)
    assert g.get_transaction("T-42") == t
    assert g.get_transaction("MISSING") is None


def test_get_account():
    g = TransactionGraph()
    a = make_account(account_id="A")
    g.add_account(a)
    assert g.get_account("A") == a
    assert g.get_account("MISSING") is None


def test_window_out_filters_by_time():
    g = TransactionGraph()
    for i in range(5):
        g.add_transaction(make_txn(txn_id=f"T-{i}", src="A", dst="B", occurred_at=t_at(i * 60)))
    out = g.window_out("A", since=t_at(60), until=t_at(180))
    assert {t.txn_id for t in out} == {"T-1", "T-2", "T-3"}


def test_window_in_filters_by_time():
    g = TransactionGraph()
    for i in range(5):
        g.add_transaction(make_txn(txn_id=f"T-{i}", src=f"A{i}", dst="B", occurred_at=t_at(i * 60)))
    inb = g.window_in("B", since=t_at(120), until=t_at(240))
    assert {t.txn_id for t in inb} == {"T-2", "T-3", "T-4"}


def test_out_after_returns_sorted_by_time():
    g = TransactionGraph()
    g.add_transaction(make_txn(txn_id="T-2", src="A", dst="B", occurred_at=t_at(120)))
    g.add_transaction(make_txn(txn_id="T-1", src="A", dst="C", occurred_at=t_at(60)))
    out = g.out_after("A", after=t_at(0), within=timedelta(seconds=200))
    assert [t.txn_id for t in out] == ["T-1", "T-2"]


def test_has_account_lookup():
    g = TransactionGraph()
    g.add_account(make_account(account_id="A"))
    assert g.has_account("A")
    assert not g.has_account("B")


def test_neighbors_dedup():
    """Multiple txns A → B → just one neighbor entry."""
    g = TransactionGraph()
    g.add_transaction(make_txn(txn_id="T-1", src="A", dst="B"))
    g.add_transaction(make_txn(txn_id="T-2", src="A", dst="B"))
    assert g.neighbors_out("A") == {"B"}
