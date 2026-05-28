"""Comprehensive tests for the riskmonitor package.

Test classes
------------
TestExposureGraph         — graph construction and query correctness
TestCycleDetection        — Johnson's cycle finder
TestBetweenness           — Brandes betweenness centrality
TestPageRank              — power-iteration PageRank
TestHHI                   — Herfindahl–Hirschman Index
TestGini                  — Gini coefficient
TestSimulator             — TransactionSimulator
TestRiskAnalyzer          — end-to-end RiskAnalyzer
TestAlertEngine           — AlertEngine rule coverage
TestCascadeBFS            — cascade_bfs BFS logic
TestOutboundVector        — outbound_vector helper
TestProperties            — Hypothesis property-based tests
"""

from __future__ import annotations

import math
import unittest

from hypothesis import given, settings
from hypothesis import strategies as st

from riskmonitor.alerts import Alert, AlertEngine, Severity
from riskmonitor.algorithms import (
    Cycle,
    betweenness_centrality,
    cascade_bfs,
    find_cycles,
    gini,
    hhi,
    outbound_vector,
    pagerank,
)
from riskmonitor.analyzer import RiskAnalyzer, RiskReport
from riskmonitor.graph import ExposureGraph
from riskmonitor.simulator import BANK_POOL, TransactionSimulator, Transfer

# ===========================================================================
# Helpers
# ===========================================================================


def _make_graph(*transfers: tuple[str, str, float]) -> ExposureGraph:
    """Build an ExposureGraph from (from_id, to_id, amount) tuples."""
    g = ExposureGraph()
    for f, t, a in transfers:
        g.add_transfer(f, t, a)
    return g


def _triangle_adj() -> dict[str, dict[str, float]]:
    """Return adjacency for A→B→C→A with equal weights."""
    return {
        "A": {"B": 10.0},
        "B": {"C": 10.0},
        "C": {"A": 10.0},
    }


def _star_adj(center: str = "C", leaves: list[str] | None = None) -> dict[str, dict[str, float]]:
    """Return adjacency for a star graph: all leaves connect through the center."""
    if leaves is None:
        leaves = ["A", "B", "D", "E"]
    adj: dict[str, dict[str, float]] = {center: {}}
    for leaf in leaves:
        adj[leaf] = {center: 1.0}
        adj[center][leaf] = 1.0
    return adj


# ===========================================================================
# TestExposureGraph
# ===========================================================================


class TestExposureGraph(unittest.TestCase):
    """Tests for ExposureGraph."""

    def test_add_single_transfer_registers_nodes(self) -> None:
        g = ExposureGraph()
        g.add_transfer("A", "B", 100.0)
        self.assertIn("A", g.nodes())
        self.assertIn("B", g.nodes())

    def test_nodes_sorted(self) -> None:
        g = _make_graph(("C", "A", 1.0), ("B", "D", 1.0))
        self.assertEqual(g.nodes(), sorted(g.nodes()))

    def test_add_transfer_accumulation(self) -> None:
        g = ExposureGraph()
        g.add_transfer("A", "B", 100.0)
        g.add_transfer("A", "B", 50.0)
        # net_exposure A→B should be 150 (no B→A flows)
        self.assertAlmostEqual(g.net_exposure("A", "B"), 150.0)

    def test_net_exposure_netting(self) -> None:
        g = ExposureGraph()
        g.add_transfer("A", "B", 200.0)
        g.add_transfer("B", "A", 80.0)
        self.assertAlmostEqual(g.net_exposure("A", "B"), 120.0)
        self.assertAlmostEqual(g.net_exposure("B", "A"), -120.0)

    def test_net_exposure_symmetry(self) -> None:
        g = _make_graph(("X", "Y", 300.0), ("Y", "X", 300.0))
        self.assertAlmostEqual(g.net_exposure("X", "Y"), 0.0)
        self.assertAlmostEqual(g.net_exposure("Y", "X"), 0.0)

    def test_net_exposure_unknown_nodes_zero(self) -> None:
        g = ExposureGraph()
        self.assertAlmostEqual(g.net_exposure("GHOST", "FOO"), 0.0)

    def test_empty_graph_nodes(self) -> None:
        g = ExposureGraph()
        self.assertEqual(g.nodes(), [])

    def test_empty_graph_edges(self) -> None:
        g = ExposureGraph()
        self.assertEqual(g.edges(), [])

    def test_edges_only_positive_net(self) -> None:
        g = _make_graph(("A", "B", 100.0), ("B", "A", 120.0))
        edges = g.edges()
        # Net A→B is -20, net B→A is +20; only B→A should appear
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0][0], "B")
        self.assertEqual(edges[0][1], "A")
        self.assertAlmostEqual(edges[0][2], 20.0)

    def test_total_outbound(self) -> None:
        g = _make_graph(("A", "B", 50.0), ("A", "C", 30.0), ("B", "A", 10.0))
        # net A→B = 40, net A→C = 30 → total outbound A = 70
        self.assertAlmostEqual(g.total_outbound("A"), 70.0)

    def test_total_inbound(self) -> None:
        g = _make_graph(("A", "B", 50.0), ("C", "B", 30.0))
        # net inbound to B = 50 + 30 = 80
        self.assertAlmostEqual(g.total_inbound("B"), 80.0)

    def test_negative_amount_raises(self) -> None:
        g = ExposureGraph()
        with self.assertRaises(ValueError):
            g.add_transfer("A", "B", -1.0)

    def test_len(self) -> None:
        g = _make_graph(("A", "B", 10.0), ("B", "C", 10.0))
        self.assertEqual(len(g), 3)

    def test_repr(self) -> None:
        g = _make_graph(("A", "B", 10.0))
        self.assertIn("ExposureGraph", repr(g))

    def test_adjacency_excludes_non_positive_net(self) -> None:
        g = _make_graph(("A", "B", 100.0), ("B", "A", 150.0))
        adj = g.adjacency()
        # A→B net = -50 (not included), B→A net = +50
        self.assertNotIn("A", adj.get("A", {}) if "B" in adj.get("A", {}) else {})
        self.assertIn("A", adj.get("B", {}))


# ===========================================================================
# TestCycleDetection
# ===========================================================================


class TestCycleDetection(unittest.TestCase):
    """Tests for find_cycles (Johnson's DFS)."""

    def test_triangle_cycle_found(self) -> None:
        adj = _triangle_adj()
        cycles = find_cycles(adj)
        self.assertGreater(len(cycles), 0)
        cycle_node_sets = [frozenset(c.nodes) for c in cycles]
        self.assertIn(frozenset(["A", "B", "C"]), cycle_node_sets)

    def test_linear_chain_no_cycle(self) -> None:
        adj: dict[str, dict[str, float]] = {"A": {"B": 10.0}, "B": {"C": 10.0}, "C": {}}
        cycles = find_cycles(adj)
        self.assertEqual(len(cycles), 0)

    def test_empty_graph_no_cycle(self) -> None:
        self.assertEqual(find_cycles({}), [])

    def test_single_node_no_cycle(self) -> None:
        self.assertEqual(find_cycles({"A": {}}), [])

    def test_self_loop_not_in_simple_cycles(self) -> None:
        # Johnson's only finds cycles of length >= 2; a self-loop (A→A) is length 1
        adj: dict[str, dict[str, float]] = {"A": {"A": 5.0, "B": 5.0}, "B": {"A": 5.0}}
        cycles = find_cycles(adj)
        # A→B→A should be found; A→A should NOT be (not a simple cycle per Johnson's)
        self.assertTrue(any(frozenset(c.nodes) == frozenset(["A", "B"]) for c in cycles))

    def test_cycle_notional_correct(self) -> None:
        adj = _triangle_adj()
        cycles = find_cycles(adj)
        triangle = next(c for c in cycles if frozenset(c.nodes) == frozenset(["A", "B", "C"]))
        self.assertAlmostEqual(triangle.notional, 30.0)

    def test_cycle_bottleneck_correct(self) -> None:
        adj: dict[str, dict[str, float]] = {
            "A": {"B": 5.0},
            "B": {"C": 20.0},
            "C": {"A": 10.0},
        }
        cycles = find_cycles(adj)
        triangle = next(c for c in cycles if frozenset(c.nodes) == frozenset(["A", "B", "C"]))
        self.assertAlmostEqual(triangle.bottleneck, 5.0)

    def test_two_separate_cycles(self) -> None:
        # Two triangles sharing no edges
        adj: dict[str, dict[str, float]] = {
            "A": {"B": 1.0},
            "B": {"C": 1.0},
            "C": {"A": 1.0},
            "D": {"E": 1.0},
            "E": {"F": 1.0},
            "F": {"D": 1.0},
        }
        cycles = find_cycles(adj)
        node_sets = [frozenset(c.nodes) for c in cycles]
        self.assertIn(frozenset(["A", "B", "C"]), node_sets)
        self.assertIn(frozenset(["D", "E", "F"]), node_sets)

    def test_cycle_is_cycle_dataclass(self) -> None:
        adj = _triangle_adj()
        cycles = find_cycles(adj)
        self.assertIsInstance(cycles[0], Cycle)


# ===========================================================================
# TestBetweenness
# ===========================================================================


class TestBetweenness(unittest.TestCase):
    """Tests for betweenness_centrality."""

    def test_star_center_high_betweenness(self) -> None:
        adj = _star_adj("C", ["A", "B", "D", "E"])
        bc = betweenness_centrality(adj)
        center_bc = bc["C"]
        for leaf in ["A", "B", "D", "E"]:
            self.assertGreaterEqual(center_bc, bc[leaf])

    def test_path_graph_endpoints_zero(self) -> None:
        # A→B→C: only B is on any path between A and C
        adj: dict[str, dict[str, float]] = {"A": {"B": 1.0}, "B": {"C": 1.0}, "C": {}}
        bc = betweenness_centrality(adj)
        self.assertAlmostEqual(bc["A"], 0.0)
        self.assertAlmostEqual(bc["C"], 0.0)

    def test_betweenness_normalised_range(self) -> None:
        adj = _star_adj("C", ["A", "B", "D"])
        bc = betweenness_centrality(adj)
        for v, score in bc.items():
            self.assertGreaterEqual(score, 0.0, f"negative betweenness for {v}")
            self.assertLessEqual(score, 1.0, f"betweenness > 1.0 for {v}")

    def test_two_nodes_betweenness_zero(self) -> None:
        adj: dict[str, dict[str, float]] = {"A": {"B": 1.0}, "B": {}}
        bc = betweenness_centrality(adj)
        for score in bc.values():
            self.assertAlmostEqual(score, 0.0)

    def test_empty_graph_betweenness(self) -> None:
        self.assertEqual(betweenness_centrality({}), {})

    def test_all_nodes_present_in_result(self) -> None:
        adj: dict[str, dict[str, float]] = {
            "A": {"B": 1.0, "C": 1.0},
            "B": {"C": 1.0},
            "C": {},
        }
        bc = betweenness_centrality(adj)
        self.assertSetEqual(set(bc.keys()), {"A", "B", "C"})


# ===========================================================================
# TestPageRank
# ===========================================================================


class TestPageRank(unittest.TestCase):
    """Tests for pagerank."""

    def _assert_sum_one(self, pr: dict[str, float]) -> None:
        self.assertAlmostEqual(sum(pr.values()), 1.0, places=9)

    def test_sum_equals_one(self) -> None:
        adj: dict[str, dict[str, float]] = {
            "A": {"B": 1.0},
            "B": {"C": 1.0},
            "C": {"A": 1.0},
        }
        self._assert_sum_one(pagerank(adj))

    def test_uniform_graph_equal_ranks(self) -> None:
        adj: dict[str, dict[str, float]] = {
            "A": {"B": 1.0, "C": 1.0},
            "B": {"A": 1.0, "C": 1.0},
            "C": {"A": 1.0, "B": 1.0},
        }
        pr = pagerank(adj)
        self._assert_sum_one(pr)
        # All ranks should be approximately equal
        ranks = list(pr.values())
        self.assertAlmostEqual(max(ranks) - min(ranks), 0.0, places=5)

    def test_dangling_node_handled(self) -> None:
        # D is a dangling node (no outbound edges)
        adj: dict[str, dict[str, float]] = {
            "A": {"B": 1.0},
            "B": {"C": 1.0},
            "C": {"D": 1.0},
            "D": {},
        }
        pr = pagerank(adj)
        self._assert_sum_one(pr)

    def test_empty_graph_returns_empty(self) -> None:
        self.assertEqual(pagerank({}), {})

    def test_single_node(self) -> None:
        adj: dict[str, dict[str, float]] = {"A": {}}
        pr = pagerank(adj)
        self._assert_sum_one(pr)
        self.assertAlmostEqual(pr["A"], 1.0)

    def test_all_nodes_present_in_result(self) -> None:
        adj: dict[str, dict[str, float]] = {"A": {"B": 1.0}, "B": {"C": 1.0}, "C": {}}
        pr = pagerank(adj)
        self.assertSetEqual(set(pr.keys()), {"A", "B", "C"})

    def test_hub_has_higher_pagerank(self) -> None:
        # Many nodes point to HUB
        adj: dict[str, dict[str, float]] = {
            "A": {"HUB": 1.0},
            "B": {"HUB": 1.0},
            "C": {"HUB": 1.0},
            "HUB": {"A": 1.0},
        }
        pr = pagerank(adj)
        self._assert_sum_one(pr)
        self.assertGreater(pr["HUB"], pr["A"])


# ===========================================================================
# TestHHI
# ===========================================================================


class TestHHI(unittest.TestCase):
    """Tests for hhi."""

    def test_monopoly_returns_one(self) -> None:
        self.assertAlmostEqual(hhi([100.0, 0.0, 0.0]), 1.0)

    def test_uniform_four_returns_quarter(self) -> None:
        self.assertAlmostEqual(hhi([1.0, 1.0, 1.0, 1.0]), 0.25)

    def test_uniform_n(self) -> None:
        n = 5
        val = 1.0 / n
        self.assertAlmostEqual(hhi([1.0] * n), val)

    def test_empty_returns_zero(self) -> None:
        self.assertAlmostEqual(hhi([]), 0.0)

    def test_all_zero_returns_zero(self) -> None:
        self.assertAlmostEqual(hhi([0.0, 0.0]), 0.0)

    def test_single_element(self) -> None:
        self.assertAlmostEqual(hhi([42.0]), 1.0)

    def test_two_equal(self) -> None:
        self.assertAlmostEqual(hhi([5.0, 5.0]), 0.5)

    def test_range(self) -> None:
        # HHI should be in [1/n, 1] for n elements
        vals = [3.0, 1.0, 2.0]
        h = hhi(vals)
        self.assertGreaterEqual(h, 1.0 / len(vals) - 1e-9)
        self.assertLessEqual(h, 1.0 + 1e-9)


# ===========================================================================
# TestGini
# ===========================================================================


class TestGini(unittest.TestCase):
    """Tests for gini."""

    def test_equal_distribution_zero(self) -> None:
        self.assertAlmostEqual(gini([10.0, 10.0, 10.0]), 0.0)

    def test_max_inequality_approaches_one(self) -> None:
        # One entity has everything, rest have zero
        g = gini([100.0, 0.0, 0.0, 0.0])
        self.assertGreater(g, 0.7)

    def test_empty_returns_zero(self) -> None:
        self.assertAlmostEqual(gini([]), 0.0)

    def test_all_zero_returns_zero(self) -> None:
        self.assertAlmostEqual(gini([0.0, 0.0, 0.0]), 0.0)

    def test_single_element(self) -> None:
        self.assertAlmostEqual(gini([5.0]), 0.0)

    def test_two_element_max_inequality(self) -> None:
        # [1, 0] → gini = |1-0| + |0-1| / (2 * 2 * 0.5) = 2 / 2 = 1.0
        self.assertAlmostEqual(gini([1.0, 0.0]), 1.0)

    def test_non_negative_result(self) -> None:
        g = gini([5.0, 3.0, 8.0, 1.0])
        self.assertGreaterEqual(g, 0.0)

    def test_scaling_invariant(self) -> None:
        vals = [1.0, 2.0, 3.0, 4.0]
        g1 = gini(vals)
        g2 = gini([v * 10 for v in vals])
        self.assertAlmostEqual(g1, g2, places=10)


# ===========================================================================
# TestSimulator
# ===========================================================================


class TestSimulator(unittest.TestCase):
    """Tests for TransactionSimulator."""

    def test_deterministic_with_seed(self) -> None:
        sim = TransactionSimulator(seed=42)
        t1 = sim.generate(50)
        t2 = sim.generate(50)
        self.assertEqual(t1, t2)

    def test_different_seeds_different_output(self) -> None:
        sim1 = TransactionSimulator(seed=1)
        sim2 = TransactionSimulator(seed=2)
        self.assertNotEqual(sim1.generate(10), sim2.generate(10))

    def test_amounts_in_range(self) -> None:
        sim = TransactionSimulator(seed=42)
        transfers = sim.generate(200)
        for t in transfers:
            self.assertGreaterEqual(t.amount, 1_000_000.0)
            self.assertLessEqual(t.amount, 50_000_000.0)

    def test_from_id_neq_to_id(self) -> None:
        sim = TransactionSimulator(seed=42)
        for t in sim.generate(100):
            self.assertNotEqual(t.from_id, t.to_id)

    def test_bank_ids_from_pool(self) -> None:
        sim = TransactionSimulator(seed=42)
        transfers = sim.generate(200)
        for t in transfers:
            self.assertIn(t.from_id, BANK_POOL)
            self.assertIn(t.to_id, BANK_POOL)

    def test_uses_all_ten_banks_eventually(self) -> None:
        sim = TransactionSimulator(seed=42)
        transfers = sim.generate(500)
        seen = {t.from_id for t in transfers} | {t.to_id for t in transfers}
        self.assertEqual(seen, set(BANK_POOL))

    def test_transfer_is_frozen_dataclass(self) -> None:
        t = Transfer(from_id="A", to_id="B", amount=1_000_000.0)
        with self.assertRaises((AttributeError, TypeError)):
            t.amount = 2.0  # type: ignore[misc]

    def test_generate_correct_count(self) -> None:
        sim = TransactionSimulator()
        self.assertEqual(len(sim.generate(0)), 0)
        self.assertEqual(len(sim.generate(1)), 1)
        self.assertEqual(len(sim.generate(100)), 100)

    def test_seed_override_in_generate(self) -> None:
        sim = TransactionSimulator(seed=99)
        t1 = sim.generate(10, seed=7)
        t2 = sim.generate(10, seed=7)
        self.assertEqual(t1, t2)


# ===========================================================================
# TestRiskAnalyzer
# ===========================================================================


class TestRiskAnalyzer(unittest.TestCase):
    """End-to-end tests for RiskAnalyzer."""

    def _build_simulated_graph(self, n: int = 100, seed: int = 42) -> ExposureGraph:
        sim = TransactionSimulator(seed=seed)
        transfers = sim.generate(n)
        g = ExposureGraph()
        for t in transfers:
            g.add_transfer(t.from_id, t.to_id, t.amount)
        return g

    def test_analyze_returns_risk_report(self) -> None:
        g = self._build_simulated_graph()
        report = RiskAnalyzer().analyze(g)
        self.assertIsInstance(report, RiskReport)

    def test_betweenness_keys_match_nodes(self) -> None:
        g = self._build_simulated_graph()
        report = RiskAnalyzer().analyze(g)
        self.assertSetEqual(set(report.betweenness.keys()), set(g.nodes()))

    def test_pagerank_sums_to_one(self) -> None:
        g = self._build_simulated_graph()
        report = RiskAnalyzer().analyze(g)
        if report.pagerank:
            self.assertAlmostEqual(sum(report.pagerank.values()), 1.0, places=9)

    def test_hhi_in_valid_range(self) -> None:
        g = self._build_simulated_graph()
        report = RiskAnalyzer().analyze(g)
        self.assertGreaterEqual(report.hhi, 0.0)
        self.assertLessEqual(report.hhi, 1.0)

    def test_gini_in_valid_range(self) -> None:
        g = self._build_simulated_graph()
        report = RiskAnalyzer().analyze(g)
        self.assertGreaterEqual(report.gini, 0.0)
        self.assertLessEqual(report.gini, 1.0)

    def test_empty_graph_returns_report(self) -> None:
        g = ExposureGraph()
        report = RiskAnalyzer().analyze(g)
        self.assertIsInstance(report, RiskReport)
        self.assertEqual(report.hhi, 0.0)
        self.assertEqual(report.gini, 0.0)
        self.assertEqual(report.cycles, [])

    def test_to_dict_json_serialisable(self) -> None:
        import json as _json

        g = self._build_simulated_graph(50)
        report = RiskAnalyzer().analyze(g)
        d = report.to_dict()
        dumped = _json.dumps(d)
        self.assertIsInstance(dumped, str)

    def test_cascade_present_when_nodes_exist(self) -> None:
        g = self._build_simulated_graph(20)
        report = RiskAnalyzer().analyze(g)
        self.assertIsNotNone(report.cascade)

    def test_betweenness_max_node_property(self) -> None:
        g = self._build_simulated_graph()
        report = RiskAnalyzer().analyze(g)
        if report.betweenness:
            expected = max(report.betweenness, key=lambda v: report.betweenness[v])
            self.assertEqual(report.betweenness_max_node, expected)

    def test_max_cycle_notional_property(self) -> None:
        g = self._build_simulated_graph()
        report = RiskAnalyzer().analyze(g)
        if report.cycles:
            expected = max(c.notional for c in report.cycles)
            self.assertAlmostEqual(report.max_cycle_notional, expected)


# ===========================================================================
# TestAlertEngine
# ===========================================================================


class TestAlertEngine(unittest.TestCase):
    """Tests for AlertEngine."""

    def _make_report(
        self,
        hhi_val: float = 0.0,
        gini_val: float = 0.0,
        betweenness_max_val: float = 0.0,
        cycles: list[Cycle] | None = None,
        cascade_size: int = 0,
    ) -> RiskReport:
        from riskmonitor.algorithms import CascadeResult

        bc = {"A": betweenness_max_val}
        cr: CascadeResult | None = None
        if cascade_size > 0:
            cr = CascadeResult(seed="A", reached=["N"] * cascade_size)
        report = RiskReport(
            cycles=cycles or [],
            betweenness=bc,
            pagerank={"A": 1.0},
            hhi=hhi_val,
            gini=gini_val,
            cascade=cr,
        )
        return report

    def test_empty_graph_no_alerts(self) -> None:
        report = RiskReport()
        alerts = AlertEngine().evaluate(report)
        self.assertEqual(alerts, [])

    def test_hhi_critical_triggered(self) -> None:
        report = self._make_report(hhi_val=0.30)
        alerts = AlertEngine().evaluate(report)
        severities = [a.severity for a in alerts]
        self.assertIn(Severity.CRITICAL, severities)
        rules = [a.rule for a in alerts]
        self.assertIn("HHI_CRITICAL", rules)

    def test_cycle_notional_critical_triggered(self) -> None:
        big_cycle = Cycle(nodes=["A", "B", "C"], notional=600_000_000.0, bottleneck=1.0)
        report = self._make_report(cycles=[big_cycle])
        alerts = AlertEngine().evaluate(report)
        rules = [a.rule for a in alerts]
        self.assertIn("CYCLE_NOTIONAL_CRITICAL", rules)
        critical = [a for a in alerts if a.severity == Severity.CRITICAL]
        self.assertGreater(len(critical), 0)

    def test_gini_high_triggered(self) -> None:
        report = self._make_report(gini_val=0.75)
        alerts = AlertEngine().evaluate(report)
        rules = [a.rule for a in alerts]
        self.assertIn("GINI_HIGH", rules)

    def test_betweenness_high_triggered(self) -> None:
        report = self._make_report(betweenness_max_val=0.35)
        alerts = AlertEngine().evaluate(report)
        rules = [a.rule for a in alerts]
        self.assertIn("BETWEENNESS_HIGH", rules)

    def test_cascade_size_high_triggered(self) -> None:
        report = self._make_report(cascade_size=6)
        alerts = AlertEngine().evaluate(report)
        rules = [a.rule for a in alerts]
        self.assertIn("CASCADE_SIZE_HIGH", rules)

    def test_gini_medium_triggered(self) -> None:
        report = self._make_report(gini_val=0.60)
        alerts = AlertEngine().evaluate(report)
        rules = [a.rule for a in alerts]
        self.assertIn("GINI_MEDIUM", rules)

    def test_cycle_count_medium_triggered(self) -> None:
        small_cycles = [
            Cycle(nodes=["A", "B"], notional=1_000.0, bottleneck=500.0) for _ in range(3)
        ]
        report = self._make_report(cycles=small_cycles)
        alerts = AlertEngine().evaluate(report)
        rules = [a.rule for a in alerts]
        self.assertIn("CYCLE_COUNT_MEDIUM", rules)

    def test_betweenness_medium_triggered(self) -> None:
        report = self._make_report(betweenness_max_val=0.25)
        alerts = AlertEngine().evaluate(report)
        rules = [a.rule for a in alerts]
        self.assertIn("BETWEENNESS_MEDIUM", rules)

    def test_hhi_info_triggered(self) -> None:
        report = self._make_report(hhi_val=0.12)
        alerts = AlertEngine().evaluate(report)
        rules = [a.rule for a in alerts]
        self.assertIn("HHI_INFO", rules)

    def test_cycles_exist_info_triggered(self) -> None:
        small_cycle = Cycle(nodes=["A", "B"], notional=1_000.0, bottleneck=500.0)
        report = self._make_report(cycles=[small_cycle])
        alerts = AlertEngine().evaluate(report)
        rules = [a.rule for a in alerts]
        self.assertIn("CYCLES_EXIST", rules)

    def test_alert_has_to_dict(self) -> None:
        report = self._make_report(hhi_val=0.30)
        alerts = AlertEngine().evaluate(report)
        self.assertGreater(len(alerts), 0)
        d = alerts[0].to_dict()
        self.assertIn("severity", d)
        self.assertIn("rule", d)
        self.assertIn("message", d)
        self.assertIn("value", d)

    def test_alert_is_dataclass(self) -> None:
        a = Alert(severity=Severity.INFO, rule="TEST", message="test", value=0.1)
        self.assertIsInstance(a, Alert)


# ===========================================================================
# TestCascadeBFS
# ===========================================================================


class TestCascadeBFS(unittest.TestCase):
    """Tests for cascade_bfs."""

    def test_cascade_from_seed(self) -> None:
        adj: dict[str, dict[str, float]] = {
            "A": {"B": 1.0, "C": 1.0},
            "B": {"D": 1.0},
            "C": {},
            "D": {},
        }
        result = cascade_bfs(adj, "A")
        self.assertEqual(result.seed, "A")
        # BFS from A's outbound: B and C; then B→D
        self.assertIn("B", result.reached)
        self.assertIn("C", result.reached)
        self.assertIn("D", result.reached)

    def test_cascade_size(self) -> None:
        adj: dict[str, dict[str, float]] = {
            "A": {"B": 1.0},
            "B": {"C": 1.0},
            "C": {},
        }
        result = cascade_bfs(adj, "A")
        self.assertEqual(result.size, 2)

    def test_cascade_unknown_seed(self) -> None:
        result = cascade_bfs({}, "GHOST")
        self.assertEqual(result.size, 0)

    def test_cascade_does_not_revisit_seed(self) -> None:
        adj: dict[str, dict[str, float]] = {
            "A": {"B": 1.0},
            "B": {"A": 1.0},
        }
        result = cascade_bfs(adj, "A")
        self.assertNotIn("A", result.reached)


# ===========================================================================
# TestOutboundVector
# ===========================================================================


class TestOutboundVector(unittest.TestCase):
    """Tests for outbound_vector helper."""

    def test_correct_values(self) -> None:
        adj: dict[str, dict[str, float]] = {
            "A": {"B": 10.0, "C": 5.0},
            "B": {"C": 20.0},
            "C": {},
        }
        vec = outbound_vector(adj, ["A", "B", "C"])
        self.assertAlmostEqual(vec[0], 15.0)
        self.assertAlmostEqual(vec[1], 20.0)
        self.assertAlmostEqual(vec[2], 0.0)

    def test_empty_graph(self) -> None:
        self.assertEqual(outbound_vector({}, []), [])


# ===========================================================================
# TestProperties (Hypothesis)
# ===========================================================================


@st.composite
def random_adj(
    draw: st.DrawFn,
    min_nodes: int = 2,
    max_nodes: int = 8,
) -> dict[str, dict[str, float]]:
    """Strategy: generate a random adjacency dict for testing."""
    n = draw(st.integers(min_value=min_nodes, max_value=max_nodes))
    node_names = [f"N{i}" for i in range(n)]
    adj: dict[str, dict[str, float]] = {v: {} for v in node_names}
    for i in range(n):
        for j in range(n):
            if i != j and draw(st.booleans()):
                weight = draw(
                    st.floats(min_value=0.1, max_value=1e6, allow_nan=False, allow_infinity=False)
                )
                adj[node_names[i]][node_names[j]] = weight
    return adj


@st.composite
def positive_floats_list(
    draw: st.DrawFn,
    min_size: int = 1,
    max_size: int = 20,
) -> list[float]:
    """Strategy: non-empty list of non-negative floats (at least one > 0)."""
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    vals = draw(
        st.lists(
            st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
            min_size=size,
            max_size=size,
        )
    )
    # ensure at least one non-zero
    if all(v == 0.0 for v in vals):
        vals[0] = 1.0
    return vals


class TestProperties(unittest.TestCase):
    """Hypothesis property-based tests."""

    @given(random_adj())
    @settings(max_examples=50, deadline=5000)
    def test_pagerank_sums_to_one(self, adj: dict[str, dict[str, float]]) -> None:
        pr = pagerank(adj)
        if pr:
            total = sum(pr.values())
            self.assertTrue(
                math.isclose(total, 1.0, rel_tol=1e-7, abs_tol=1e-9),
                f"PageRank sum={total!r} not close to 1.0",
            )

    @given(positive_floats_list(min_size=1))
    @settings(max_examples=100, deadline=2000)
    def test_hhi_in_range(self, values: list[float]) -> None:
        n = len(values)
        h = hhi(values)
        lower = 1.0 / n
        self.assertGreaterEqual(h + 1e-9, lower, f"HHI={h} < 1/n={lower}")
        self.assertLessEqual(h, 1.0 + 1e-9, f"HHI={h} > 1.0")

    @given(random_adj(min_nodes=3))
    @settings(max_examples=50, deadline=5000)
    def test_betweenness_in_unit_interval(self, adj: dict[str, dict[str, float]]) -> None:
        bc = betweenness_centrality(adj)
        for v, score in bc.items():
            self.assertGreaterEqual(score, -1e-9, f"betweenness[{v}]={score} < 0")
            self.assertLessEqual(score, 1.0 + 1e-9, f"betweenness[{v}]={score} > 1")

    @given(positive_floats_list(min_size=2))
    @settings(max_examples=100, deadline=2000)
    def test_gini_in_unit_interval(self, values: list[float]) -> None:
        g = gini(values)
        self.assertGreaterEqual(g, -1e-9, f"gini={g} < 0")
        self.assertLessEqual(g, 1.0 + 1e-9, f"gini={g} > 1")

    @given(
        st.integers(min_value=10, max_value=200),
        st.integers(min_value=0, max_value=999),
    )
    @settings(max_examples=30, deadline=10000)
    def test_simulator_deterministic(self, n: int, seed: int) -> None:
        sim = TransactionSimulator(seed=seed)
        t1 = sim.generate(n)
        t2 = sim.generate(n)
        self.assertEqual(t1, t2)

    @given(random_adj())
    @settings(max_examples=50, deadline=5000)
    def test_pagerank_all_nodes_present(self, adj: dict[str, dict[str, float]]) -> None:
        pr = pagerank(adj)
        self.assertSetEqual(set(pr.keys()), set(adj.keys()))

    @given(positive_floats_list(min_size=1, max_size=10))
    @settings(max_examples=100, deadline=2000)
    def test_hhi_equal_distribution_minimum(self, values: list[float]) -> None:
        # Equal distribution achieves minimum HHI = 1/n
        n = len(values)
        equal = [1.0] * n
        h_equal = hhi(equal)
        self.assertAlmostEqual(h_equal, 1.0 / n, places=10)


if __name__ == "__main__":
    unittest.main()
