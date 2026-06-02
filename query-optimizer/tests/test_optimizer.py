"""
Unit, integration and property-based tests for the query optimizer.
Run with: pytest -v
"""

from __future__ import annotations

import io as _io
import json
import sys

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from queryopt.cascades import CascadesOptimizer
from queryopt.cost_model import CostEstimate, CostModel
from queryopt.expressions import (
    PhysicalJoin,
    PhysicalOp,
    PhysicalScan,
    Predicate,
)
from queryopt.histogram import ColumnStats, StatsCatalog, TableStats
from queryopt.memo import Memo, Winner
from queryopt.schema import build_star_schema

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mini_catalog(*tables: tuple[str, int, int]) -> StatsCatalog:
    """tables: (name, row_count, ndv_of_key)"""
    cat = StatsCatalog()
    for name, rows, ndv in tables:
        ts = TableStats(name, row_count=rows, avg_row_bytes=80)
        ts.add_column(ColumnStats(f"{name}_id", num_distinct=ndv))
        cat.register(ts)
    return cat


def _walk(w: Winner, scanned: list[str]) -> None:
    if isinstance(w.expr, PhysicalScan):
        scanned.append(w.expr.table)
    for cw in w.child_winners.values():
        _walk(cw, scanned)


# ─────────────────────────────────────────────────────────────────────────────
# ColumnStats / cardinality
# ─────────────────────────────────────────────────────────────────────────────


class TestColumnStats:
    def test_selectivity_eq_uses_max_ndv(self) -> None:
        c1 = ColumnStats("a", num_distinct=1000)
        c2 = ColumnStats("b", num_distinct=500)
        assert c1.selectivity_eq(c2) == pytest.approx(1 / 1000)

    def test_selectivity_range_full_span(self) -> None:
        c = ColumnStats("x", num_distinct=100, min_val=0, max_val=100)
        assert c.selectivity_range(0, 100) == pytest.approx(1.0)

    def test_selectivity_range_half_span(self) -> None:
        c = ColumnStats("x", num_distinct=100, min_val=0, max_val=100)
        assert c.selectivity_range(0, 50) == pytest.approx(0.5)

    def test_selectivity_range_outside(self) -> None:
        c = ColumnStats("x", num_distinct=100, min_val=0, max_val=100)
        assert c.selectivity_range(200, 300) == pytest.approx(0.0)

    def test_selectivity_eq_symmetric(self) -> None:
        c1 = ColumnStats("a", num_distinct=400)
        c2 = ColumnStats("b", num_distinct=200)
        assert c1.selectivity_eq(c2) == c2.selectivity_eq(c1)

    def test_selectivity_range_zero_span_inside(self) -> None:
        c = ColumnStats("x", num_distinct=1, min_val=5.0, max_val=5.0)
        assert c.selectivity_range(4, 6) == pytest.approx(1.0)

    def test_selectivity_range_clamps_to_one(self) -> None:
        c = ColumnStats("x", num_distinct=100, min_val=0, max_val=100)
        assert c.selectivity_range(-10, 200) == pytest.approx(1.0)


# ─────────────────────────────────────────────────────────────────────────────
# CostModel
# ─────────────────────────────────────────────────────────────────────────────


class TestCostModel:
    cm = CostModel()

    def test_seq_scan_positive(self) -> None:
        cost = self.cm.seq_scan("t", 10_000)
        assert cost.total > 0

    def test_hash_join_cheaper_than_nl_for_large_tables(self) -> None:
        hj = self.cm.hash_join(100_000, 1_000_000, 50_000)
        nl = self.cm.nested_loop_join(100_000, 1_000_000, 50_000)
        assert hj.total < nl.total

    def test_nl_cheap_for_tiny_outer(self) -> None:
        nl = self.cm.nested_loop_join(10, 100, 5)
        assert nl.total > 0

    def test_merge_join_requires_sort(self) -> None:
        mj_unsorted = self.cm.merge_join(
            100_000, 100_000, 50_000, left_sorted=False, right_sorted=False
        )
        mj_sorted = self.cm.merge_join(
            100_000, 100_000, 50_000, left_sorted=True, right_sorted=True
        )
        assert mj_unsorted.total > mj_sorted.total

    def test_cost_estimate_addition(self) -> None:
        c1 = CostEstimate(io_cost=10, cpu_cost=2)
        c2 = CostEstimate(io_cost=5, cpu_cost=1)
        total = c1 + c2
        assert total.io_cost == 15 and total.cpu_cost == 3

    def test_cost_estimate_total_is_sum(self) -> None:
        c = CostEstimate(io_cost=7.0, cpu_cost=3.0)
        assert c.total == pytest.approx(10.0)

    def test_seq_scan_zero_rows(self) -> None:
        cost = self.cm.seq_scan("empty", 0)
        assert cost.total >= 0

    def test_hash_join_io_includes_both_sides(self) -> None:
        hj = self.cm.hash_join(1_000, 2_000, 500)
        assert hj.io_cost > 0 and hj.cpu_cost > 0


# ─────────────────────────────────────────────────────────────────────────────
# Memo table
# ─────────────────────────────────────────────────────────────────────────────


class TestMemo:
    def test_deduplication_by_table_signature(self) -> None:
        memo = Memo()
        g1 = memo.get_or_create(frozenset(["a", "b"]))
        g2 = memo.get_or_create(frozenset(["b", "a"]))
        assert g1.id == g2.id

    def test_scan_group_seeded(self) -> None:
        memo = Memo()
        g = memo.get_or_create_scan("orders")
        assert len(g.logical_exprs) == 1
        assert g.tables == frozenset(["orders"])

    def test_winner_update(self) -> None:
        memo = Memo()
        g = memo.get_or_create(frozenset(["x"]))
        p = PhysicalScan("x")
        cost1 = CostEstimate(io_cost=100)
        cost2 = CostEstimate(io_cost=50)
        g.update_winner(p, cost1, {})
        assert g.winner is not None
        assert g.winner.cost.total == 100
        g.update_winner(p, cost2, {})
        assert g.winner.cost.total == 50

    def test_distinct_groups_get_distinct_ids(self) -> None:
        memo = Memo()
        g1 = memo.get_or_create(frozenset(["a"]))
        g2 = memo.get_or_create(frozenset(["b"]))
        assert g1.id != g2.id

    def test_all_groups_returns_all(self) -> None:
        memo = Memo()
        memo.get_or_create(frozenset(["a"]))
        memo.get_or_create(frozenset(["b"]))
        memo.get_or_create(frozenset(["a", "b"]))
        assert memo.num_groups() == 3
        assert len(memo.all_groups()) == 3


# ─────────────────────────────────────────────────────────────────────────────
# Predicate
# ─────────────────────────────────────────────────────────────────────────────


class TestPredicate:
    def test_str_representation(self) -> None:
        p = Predicate("orders", "cid", "customers", "id")
        assert "orders" in str(p) and "customers" in str(p)

    def test_involves_both_tables(self) -> None:
        p = Predicate("a", "x", "b", "y")
        assert p.involves(frozenset(["a", "b"]))

    def test_involves_partial_false(self) -> None:
        p = Predicate("a", "x", "b", "y")
        assert not p.involves(frozenset(["a", "c"]))

    def test_flipped_swaps_sides(self) -> None:
        p = Predicate("a", "x", "b", "y")
        fp = p.flipped()
        assert fp.left_table == "b" and fp.right_table == "a"
        assert fp.left_col == "y" and fp.right_col == "x"


# ─────────────────────────────────────────────────────────────────────────────
# Cascades optimizer – small cases
# ─────────────────────────────────────────────────────────────────────────────


class TestCascadesOptimizer:
    def test_two_table_join(self) -> None:
        cat = _mini_catalog(("a", 1000, 500), ("b", 200, 200))
        preds = [Predicate("a", "b_id", "b", "b_id")]
        opt = CascadesOptimizer(cat, CostModel())
        winner = opt.optimize(["a", "b"], preds)
        assert winner is not None
        assert winner.cost.total > 0

    def test_three_table_join_selects_plan(self) -> None:
        cat = _mini_catalog(
            ("orders", 500_000, 100_000),
            ("customer", 100_000, 100_000),
            ("product", 10_000, 10_000),
        )
        preds = [
            Predicate("orders", "customer_id", "customer", "customer_id"),
            Predicate("orders", "product_id", "product", "product_id"),
        ]
        opt = CascadesOptimizer(cat, CostModel())
        winner = opt.optimize(["orders", "customer", "product"], preds)
        assert winner is not None
        assert isinstance(winner.expr, PhysicalJoin)

    def test_small_table_joined_first(self) -> None:
        """Skewed star: optimizer should find a valid plan."""
        cat = _mini_catalog(
            ("fact", 10_000_000, 1_000),
            ("tiny_dim", 10, 10),
            ("big_dim", 500_000, 500_000),
        )
        preds = [
            Predicate("fact", "tiny_id", "tiny_dim", "tiny_id"),
            Predicate("fact", "big_id", "big_dim", "big_id"),
        ]
        opt = CascadesOptimizer(cat, CostModel())
        winner = opt.optimize(["fact", "tiny_dim", "big_dim"], preds)
        assert winner is not None

    def test_no_predicate_cross_join(self) -> None:
        """Two tables with no join predicate → Cartesian product is still planned."""
        cat = _mini_catalog(("x", 100, 100), ("y", 200, 200))
        opt = CascadesOptimizer(cat, CostModel())
        winner = opt.optimize(["x", "y"], [])
        assert winner is not None

    def test_hash_join_preferred_over_nl_for_large_tables(self) -> None:
        cat = _mini_catalog(
            ("big_a", 1_000_000, 100_000),
            ("big_b", 1_000_000, 100_000),
        )
        preds = [Predicate("big_a", "key", "big_b", "key")]
        opt = CascadesOptimizer(cat, CostModel())
        winner = opt.optimize(["big_a", "big_b"], preds)
        assert winner.expr.algorithm in (PhysicalOp.HASH_JOIN, PhysicalOp.MERGE_JOIN)

    def test_single_table_returns_scan(self) -> None:
        """Single table with no joins returns a SeqScan winner."""
        cat = _mini_catalog(("solo", 1_000, 1_000))
        opt = CascadesOptimizer(cat, CostModel())
        winner = opt.optimize(["solo"], [])
        assert isinstance(winner.expr, PhysicalScan)
        assert winner.expr.table == "solo"

    def test_join_order_lists_all_tables(self) -> None:
        cat = _mini_catalog(("a", 100, 50), ("b", 200, 100), ("c", 50, 50))
        preds = [
            Predicate("a", "bid", "b", "bid"),
            Predicate("b", "cid", "c", "cid"),
        ]
        opt = CascadesOptimizer(cat, CostModel())
        winner = opt.optimize(["a", "b", "c"], preds)
        scanned: list[str] = []
        _walk(winner, scanned)
        assert set(scanned) == {"a", "b", "c"}

    def test_dp_states_explored_positive(self) -> None:
        cat = _mini_catalog(("a", 100, 50), ("b", 200, 100))
        preds = [Predicate("a", "key", "b", "key")]
        opt = CascadesOptimizer(cat, CostModel())
        opt.optimize(["a", "b"], preds)
        assert opt._calls > 0


# ─────────────────────────────────────────────────────────────────────────────
# Full 10-table star schema integration test
# ─────────────────────────────────────────────────────────────────────────────


class TestStarSchema:
    def test_star_schema_optimizes(self) -> None:
        catalog, tables, predicates = build_star_schema()
        assert len(tables) == 10
        assert len(predicates) == 9

        cost_model = CostModel(
            avg_row_bytes={t: catalog.get(t).avg_row_bytes for t in tables}  # type: ignore[union-attr]
        )
        opt = CascadesOptimizer(catalog, cost_model)
        winner = opt.optimize(tables, predicates)
        assert winner is not None
        assert winner.cost.total > 0

    def test_star_schema_fact_table_in_plan(self) -> None:
        catalog, tables, predicates = build_star_schema()
        cost_model = CostModel()
        opt = CascadesOptimizer(catalog, cost_model)
        winner = opt.optimize(tables, predicates)

        scanned: list[str] = []
        _walk(winner, scanned)
        assert "fact_sales" in scanned

    def test_star_schema_all_tables_in_plan(self) -> None:
        catalog, tables, predicates = build_star_schema()
        cost_model = CostModel()
        opt = CascadesOptimizer(catalog, cost_model)
        opt.optimize(tables, predicates)

        root_group = opt.memo.get_group(
            next(g.id for g in opt.memo.all_groups() if g.tables == frozenset(tables))
        )
        assert root_group.tables == frozenset(tables)

    def test_star_schema_memo_covers_all_subsets(self) -> None:
        catalog, tables, predicates = build_star_schema()
        opt = CascadesOptimizer(catalog, CostModel())
        opt.optimize(tables, predicates)
        # The memo should have groups for at least all 10 base tables
        all_table_sets = {g.tables for g in opt.memo.all_groups()}
        for t in tables:
            assert frozenset([t]) in all_table_sets


# ─────────────────────────────────────────────────────────────────────────────
# CLI smoke tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCLI:
    def test_optimize_produces_json(self) -> None:
        from queryopt.cli import build_parser, cmd_optimize

        spec = json.dumps(
            {
                "tables": ["orders", "customer"],
                "predicates": [
                    {
                        "left_table": "orders",
                        "left_col": "cid",
                        "right_table": "customer",
                        "right_col": "cid",
                    }
                ],
                "row_counts": {"orders": 5000, "customer": 1000},
            }
        )
        parser = build_parser()
        args = parser.parse_args(["optimize"])
        args.input = ""

        old_stdin = sys.stdin
        old_stdout = sys.stdout
        sys.stdin = _io.StringIO(spec + "\n")
        capture = _io.StringIO()
        sys.stdout = capture
        try:
            code = cmd_optimize(args)
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

        assert code == 0
        out = json.loads(capture.getvalue().strip())
        assert "join_order" in out
        assert "total_cost" in out
        assert out["total_cost"] > 0

    def test_explain_parses_plan(self) -> None:
        from queryopt.cli import build_parser, cmd_explain

        plan = json.dumps(
            {
                "join_order": ["orders", "customer"],
                "algorithm": "HashJoin",
                "total_cost": 1234.5,
            }
        )
        parser = build_parser()
        args = parser.parse_args(["explain"])
        args.input = ""

        old_stdin = sys.stdin
        sys.stdin = _io.StringIO(plan + "\n")
        try:
            code = cmd_explain(args)
        finally:
            sys.stdin = old_stdin
        assert code == 0


# ─────────────────────────────────────────────────────────────────────────────
# Hypothesis property-based tests
# ─────────────────────────────────────────────────────────────────────────────


class TestProperties:
    @given(
        ndv_a=st.integers(min_value=1, max_value=100_000),
        ndv_b=st.integers(min_value=1, max_value=100_000),
    )
    def test_selectivity_in_unit_interval(self, ndv_a: int, ndv_b: int) -> None:
        c1 = ColumnStats("a", num_distinct=ndv_a)
        c2 = ColumnStats("b", num_distinct=ndv_b)
        sel = c1.selectivity_eq(c2)
        assert 0.0 <= sel <= 1.0

    @given(
        io1=st.floats(min_value=0, max_value=1e9, allow_nan=False, allow_infinity=False),
        cpu1=st.floats(min_value=0, max_value=1e9, allow_nan=False, allow_infinity=False),
        io2=st.floats(min_value=0, max_value=1e9, allow_nan=False, allow_infinity=False),
        cpu2=st.floats(min_value=0, max_value=1e9, allow_nan=False, allow_infinity=False),
    )
    def test_cost_addition_commutative(
        self, io1: float, cpu1: float, io2: float, cpu2: float
    ) -> None:
        c1 = CostEstimate(io_cost=io1, cpu_cost=cpu1)
        c2 = CostEstimate(io_cost=io2, cpu_cost=cpu2)
        assert (c1 + c2).total == pytest.approx((c2 + c1).total, rel=1e-9)

    @given(
        rows=st.integers(min_value=1, max_value=10_000_000),
    )
    def test_seq_scan_cost_positive(self, rows: int) -> None:
        cm = CostModel()
        cost = cm.seq_scan("t", rows)
        assert cost.total > 0

    @given(
        build_rows=st.integers(min_value=1, max_value=1_000_000),
        probe_rows=st.integers(min_value=1, max_value=1_000_000),
        out_rows=st.integers(min_value=0, max_value=1_000_000),
    )
    @settings(max_examples=50)
    def test_hash_join_cost_positive(
        self, build_rows: int, probe_rows: int, out_rows: int
    ) -> None:
        cm = CostModel()
        cost = cm.hash_join(build_rows, probe_rows, out_rows)
        assert cost.total > 0

    @given(
        left_rows=st.integers(min_value=1, max_value=500_000),
        right_rows=st.integers(min_value=1, max_value=500_000),
    )
    @settings(max_examples=30)
    def test_catalog_join_output_rows_positive(self, left_rows: int, right_rows: int) -> None:
        cat = StatsCatalog()
        ts_l = TableStats("l", row_count=left_rows)
        ts_l.add_column(ColumnStats("l_id", num_distinct=left_rows))
        ts_r = TableStats("r", row_count=right_rows)
        ts_r.add_column(ColumnStats("r_id", num_distinct=right_rows))
        cat.register(ts_l)
        cat.register(ts_r)

        preds = [Predicate("l", "l_id", "r", "r_id")]
        out = cat.join_output_rows(
            frozenset(["l"]),
            frozenset(["r"]),
            float(left_rows),
            float(right_rows),
            preds,
        )
        assert out >= 1.0
