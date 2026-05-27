"""Comprehensive tests for the self-healing ETL framework."""

from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from selfheal.alerts.alerter import ConsoleAlerter
from selfheal.healing.strategies import HealingEngine
from selfheal.pipeline.runner import PipelineRunner, RunResult
from selfheal.quarantine.store import QuarantineStore
from selfheal.schema.drift import DriftDetector, DriftEvent, DriftType
from selfheal.schema.registry import SchemaEntry, SchemaRegistry

# ===========================================================================
# Helpers
# ===========================================================================


def _make_registry(source: str, schema: dict[str, str]) -> SchemaRegistry:
    reg = SchemaRegistry()
    reg.register(source, schema)
    return reg


# ===========================================================================
# DriftDetector tests
# ===========================================================================


class TestDriftDetectorNoDrift(unittest.TestCase):
    def test_identical_schemas_produce_no_events(self) -> None:
        schema: dict[str, str] = {"id": "int", "name": "str", "amount": "float"}
        detector = DriftDetector(schema)
        events = detector.detect(schema)
        self.assertEqual(events, [])

    def test_empty_schemas_produce_no_events(self) -> None:
        detector = DriftDetector({})
        events = detector.detect({})
        self.assertEqual(events, [])


class TestDriftDetectorColumnAdded(unittest.TestCase):
    def test_single_column_added(self) -> None:
        registered: dict[str, str] = {"id": "int"}
        batch: dict[str, str] = {"id": "int", "extra": "str"}
        events = DriftDetector(registered).detect(batch)
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev.drift_type, DriftType.COLUMN_ADDED)
        self.assertEqual(ev.column, "extra")
        self.assertIsNone(ev.old_type)
        self.assertEqual(ev.new_type, "str")
        self.assertEqual(ev.severity, "low")

    def test_multiple_columns_added(self) -> None:
        registered: dict[str, str] = {"id": "int"}
        batch: dict[str, str] = {"id": "int", "a": "str", "b": "float"}
        events = DriftDetector(registered).detect(batch)
        added = [e for e in events if e.drift_type == DriftType.COLUMN_ADDED]
        self.assertEqual(len(added), 2)


class TestDriftDetectorColumnRemoved(unittest.TestCase):
    def test_single_column_removed(self) -> None:
        registered: dict[str, str] = {"id": "int", "name": "str"}
        batch: dict[str, str] = {"id": "int"}
        events = DriftDetector(registered).detect(batch)
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev.drift_type, DriftType.COLUMN_REMOVED)
        self.assertEqual(ev.column, "name")
        self.assertEqual(ev.old_type, "str")
        self.assertIsNone(ev.new_type)
        self.assertEqual(ev.severity, "high")

    def test_all_columns_removed(self) -> None:
        registered: dict[str, str] = {"a": "int", "b": "str"}
        events = DriftDetector(registered).detect({})
        self.assertEqual(len(events), 2)
        types = {e.drift_type for e in events}
        self.assertEqual(types, {DriftType.COLUMN_REMOVED})


class TestDriftDetectorTypeChanged(unittest.TestCase):
    def test_type_change_detected(self) -> None:
        registered: dict[str, str] = {"id": "int", "amount": "float"}
        batch: dict[str, str] = {"id": "int", "amount": "str"}
        events = DriftDetector(registered).detect(batch)
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev.drift_type, DriftType.TYPE_CHANGED)
        self.assertEqual(ev.column, "amount")
        self.assertEqual(ev.old_type, "float")
        self.assertEqual(ev.new_type, "str")
        self.assertEqual(ev.severity, "medium")


class TestDriftDetectorMultipleDrifts(unittest.TestCase):
    def test_mixed_drift_events(self) -> None:
        registered: dict[str, str] = {"id": "int", "name": "str", "amount": "float"}
        # "name" removed, "status" added, "amount" type changed
        batch: dict[str, str] = {"id": "int", "amount": "str", "status": "str"}
        events = DriftDetector(registered).detect(batch)
        self.assertEqual(len(events), 3)
        drift_types = {e.drift_type for e in events}
        self.assertEqual(
            drift_types,
            {DriftType.COLUMN_REMOVED, DriftType.COLUMN_ADDED, DriftType.TYPE_CHANGED},
        )


class TestDriftDetectorInferSchema(unittest.TestCase):
    def test_infer_from_records(self) -> None:
        records: list[dict[str, object]] = [
            {"id": 1, "name": "Alice", "score": 9.5},
        ]
        schema = DriftDetector.infer_schema(records)
        self.assertEqual(schema["id"], "int")
        self.assertEqual(schema["name"], "str")
        self.assertEqual(schema["score"], "float")

    def test_infer_skips_none(self) -> None:
        records: list[dict[str, object]] = [
            {"id": None},
            {"id": 1},
        ]
        schema = DriftDetector.infer_schema(records)
        self.assertEqual(schema["id"], "int")

    def test_infer_empty_records(self) -> None:
        schema = DriftDetector.infer_schema([])
        self.assertEqual(schema, {})


# ===========================================================================
# QuarantineStore tests
# ===========================================================================


class TestQuarantineStore(unittest.TestCase):
    def setUp(self) -> None:
        self.store = QuarantineStore()

    def test_initial_count_is_zero(self) -> None:
        self.assertEqual(self.store.count(), 0)

    def test_add_increases_count(self) -> None:
        self.store.add({"id": 1}, "schema_error", "missing column", run_id="r1")
        self.assertEqual(self.store.count(), 1)

    def test_add_multiple_records(self) -> None:
        for i in range(5):
            self.store.add({"id": i}, "error_type", "detail")
        self.assertEqual(self.store.count(), 5)

    def test_all_records_returns_copy(self) -> None:
        self.store.add({"id": 1}, "err", "detail")
        records = self.store.all_records()
        self.assertEqual(len(records), 1)
        records.clear()
        # Original store should be untouched.
        self.assertEqual(self.store.count(), 1)

    def test_count_by_error_type(self) -> None:
        self.store.add({}, "type_a", "d")
        self.store.add({}, "type_a", "d")
        self.store.add({}, "type_b", "d")
        counts = self.store.count_by_error_type()
        self.assertEqual(counts["type_a"], 2)
        self.assertEqual(counts["type_b"], 1)

    def test_export_jsonl_is_valid(self) -> None:
        self.store.add({"id": 1, "val": "x"}, "err", "detail", run_id="r1")
        self.store.add({"id": 2}, "err2", "d2", run_id="r2")
        jsonl = self.store.export_jsonl()
        lines = [ln for ln in jsonl.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 2)
        for line in lines:
            obj = json.loads(line)
            self.assertIn("record", obj)
            self.assertIn("error_type", obj)
            self.assertIn("quarantined_at", obj)

    def test_export_jsonl_empty_store(self) -> None:
        self.assertEqual(self.store.export_jsonl(), "")

    def test_clear(self) -> None:
        self.store.add({}, "e", "d")
        self.store.clear()
        self.assertEqual(self.store.count(), 0)


# ===========================================================================
# HealingEngine tests
# ===========================================================================


class TestHealingEngineBackfill(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = _make_registry("src", {"id": "int", "name": "str"})
        self.engine = HealingEngine(self.registry, "src")

    def _removed_event(self, col: str, old_type: str) -> DriftEvent:
        return DriftEvent(
            column=col,
            drift_type=DriftType.COLUMN_REMOVED,
            old_type=old_type,
            new_type=None,
            severity="high",
        )

    def test_backfill_str_column(self) -> None:
        record: dict[str, object] = {"id": 1}
        events = [self._removed_event("name", "str")]
        result = self.engine.heal(record, events)
        self.assertTrue(result.healed)
        self.assertEqual(result.record["name"], "")
        self.assertIn("backfill", (result.strategy_used or ""))

    def test_backfill_int_column(self) -> None:
        record: dict[str, object] = {"name": "Alice"}
        events = [self._removed_event("id", "int")]
        result = self.engine.heal(record, events)
        self.assertTrue(result.healed)
        self.assertEqual(result.record["id"], 0)

    def test_backfill_float_column(self) -> None:
        record: dict[str, object] = {"id": 1}
        events = [self._removed_event("score", "float")]
        result = self.engine.heal(record, events)
        self.assertTrue(result.healed)
        self.assertEqual(result.record["score"], 0.0)

    def test_backfill_bool_column(self) -> None:
        record: dict[str, object] = {"id": 1}
        events = [self._removed_event("active", "bool")]
        result = self.engine.heal(record, events)
        self.assertTrue(result.healed)
        self.assertIs(result.record["active"], False)


class TestHealingEngineCoerce(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = _make_registry("src", {"id": "int", "amount": "float", "label": "str"})
        self.engine = HealingEngine(self.registry, "src")

    def _changed_event(self, col: str, old_type: str, new_type: str) -> DriftEvent:
        return DriftEvent(
            column=col,
            drift_type=DriftType.TYPE_CHANGED,
            old_type=old_type,
            new_type=new_type,
            severity="medium",
        )

    def test_coerce_str_to_int(self) -> None:
        record: dict[str, object] = {"id": "42", "amount": 1.0}
        events = [self._changed_event("id", "int", "str")]
        result = self.engine.heal(record, events)
        self.assertTrue(result.healed)
        self.assertEqual(result.record["id"], 42)

    def test_coerce_int_to_str(self) -> None:
        record: dict[str, object] = {"label": 99}
        events = [self._changed_event("label", "str", "int")]
        result = self.engine.heal(record, events)
        self.assertTrue(result.healed)
        self.assertEqual(result.record["label"], "99")

    def test_coerce_str_to_float(self) -> None:
        record: dict[str, object] = {"amount": "3.14"}
        events = [self._changed_event("amount", "float", "str")]
        result = self.engine.heal(record, events)
        self.assertTrue(result.healed)
        self.assertAlmostEqual(float(result.record["amount"]), 3.14)

    def test_coerce_fails_for_invalid_value(self) -> None:
        record: dict[str, object] = {"id": "not_a_number"}
        events = [self._changed_event("id", "int", "str")]
        result = self.engine.heal(record, events)
        self.assertFalse(result.healed)
        self.assertIsNotNone(result.failure_reason)

    def test_coerce_fails_for_missing_old_type(self) -> None:
        record: dict[str, object] = {"id": "42"}
        # old_type is None — should fail
        event = DriftEvent(
            column="id",
            drift_type=DriftType.TYPE_CHANGED,
            old_type=None,
            new_type="str",
            severity="medium",
        )
        result = self.engine.heal(record, [event])
        self.assertFalse(result.healed)


class TestHealingEngineEvolve(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = _make_registry("src", {"id": "int"})
        self.engine = HealingEngine(self.registry, "src")

    def test_evolve_adds_column_to_registry(self) -> None:
        record: dict[str, object] = {"id": 1, "status": "active"}
        event = DriftEvent(
            column="status",
            drift_type=DriftType.COLUMN_ADDED,
            old_type=None,
            new_type="str",
            severity="low",
        )
        result = self.engine.heal(record, [event])
        self.assertTrue(result.healed)
        self.assertIn("evolve", (result.strategy_used or ""))
        # Schema should be updated in registry.
        active = self.registry.get_active("src")
        self.assertIsNotNone(active)
        assert active is not None
        self.assertIn("status", active.schema)


# ===========================================================================
# SchemaRegistry tests
# ===========================================================================


class TestSchemaRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = SchemaRegistry()

    def test_register_first_schema_is_version_1(self) -> None:
        entry = self.registry.register("src", {"id": "int"})
        self.assertEqual(entry.version, 1)

    def test_register_increments_version(self) -> None:
        self.registry.register("src", {"id": "int"})
        entry2 = self.registry.register("src", {"id": "int", "name": "str"})
        self.assertEqual(entry2.version, 2)

    def test_get_active_returns_latest(self) -> None:
        self.registry.register("src", {"id": "int"})
        self.registry.register("src", {"id": "int", "name": "str"})
        active = self.registry.get_active("src")
        self.assertIsNotNone(active)
        assert active is not None
        self.assertEqual(active.version, 2)

    def test_get_active_none_for_unknown_source(self) -> None:
        self.assertIsNone(self.registry.get_active("nonexistent"))

    def test_get_history_returns_all_versions(self) -> None:
        self.registry.register("src", {"a": "int"})
        self.registry.register("src", {"a": "int", "b": "str"})
        history = self.registry.get_history("src")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].version, 1)
        self.assertEqual(history[1].version, 2)

    def test_sources_returns_registered_names(self) -> None:
        self.registry.register("s1", {"x": "int"})
        self.registry.register("s2", {"y": "str"})
        self.assertIn("s1", self.registry.sources())
        self.assertIn("s2", self.registry.sources())

    def test_json_roundtrip(self) -> None:
        self.registry.register("src", {"id": "int", "name": "str"})
        self.registry.register("src", {"id": "int", "name": "str", "score": "float"})
        raw = self.registry.to_json()
        restored = SchemaRegistry.from_json(raw)
        active = restored.get_active("src")
        self.assertIsNotNone(active)
        assert active is not None
        self.assertEqual(active.version, 2)
        self.assertIn("score", active.schema)

    def test_schema_entry_to_dict(self) -> None:
        entry = SchemaEntry(
            version=1,
            schema={"id": "int"},
            registered_at="2025-01-01T00:00:00+00:00",
        )
        d = entry.to_dict()
        self.assertEqual(d["version"], 1)
        self.assertEqual(d["schema"], {"id": "int"})


# ===========================================================================
# PipelineRunner tests
# ===========================================================================


class TestPipelineRunnerClean(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = _make_registry("orders", {"id": "int", "amount": "float"})
        self.quarantine = QuarantineStore()
        self.runner = PipelineRunner(self.registry, "orders", self.quarantine)

    def test_clean_run_loads_all_records(self) -> None:
        records: list[dict[str, object]] = [
            {"id": 1, "amount": 10.0},
            {"id": 2, "amount": 20.0},
        ]
        result = self.runner.run(records)
        self.assertEqual(result.loaded, 2)
        self.assertEqual(result.quarantined, 0)
        self.assertEqual(result.healed, 0)
        self.assertEqual(len(result.drift_events), 0)

    def test_bootstrap_with_no_prior_schema(self) -> None:
        reg = SchemaRegistry()
        q = QuarantineStore()
        runner = PipelineRunner(reg, "new_source", q)
        records: list[dict[str, object]] = [{"x": 1}]
        result = runner.run(records)
        self.assertEqual(result.loaded, 1)
        self.assertIsNotNone(reg.get_active("new_source"))


class TestPipelineRunnerBackfill(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = _make_registry(
            "orders", {"id": "int", "amount": "float", "customer": "str"}
        )
        self.quarantine = QuarantineStore()
        self.runner = PipelineRunner(self.registry, "orders", self.quarantine)

    def test_backfill_missing_column(self) -> None:
        # "customer" is missing from batch
        records: list[dict[str, object]] = [
            {"id": 1, "amount": 10.0},
            {"id": 2, "amount": 20.0},
        ]
        result = self.runner.run(records)
        self.assertEqual(result.loaded, 2)
        self.assertEqual(result.quarantined, 0)
        self.assertGreater(result.healed, 0)


class TestPipelineRunnerCoerce(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = _make_registry("orders", {"id": "int", "amount": "float"})
        self.quarantine = QuarantineStore()
        self.runner = PipelineRunner(self.registry, "orders", self.quarantine)

    def test_coerce_type_changed(self) -> None:
        # "amount" arrives as str instead of float
        records: list[dict[str, object]] = [
            {"id": 1, "amount": "9.99"},
            {"id": 2, "amount": "19.99"},
        ]
        result = self.runner.run(records)
        self.assertEqual(result.loaded, 2)
        self.assertEqual(result.quarantined, 0)


class TestPipelineRunnerQuarantine(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = _make_registry("orders", {"id": "int", "amount": "float"})
        self.quarantine = QuarantineStore()
        self.runner = PipelineRunner(self.registry, "orders", self.quarantine)

    def test_uncoercible_value_goes_to_quarantine(self) -> None:
        # "amount" type changed to str, but the value is not coercible to float
        records: list[dict[str, object]] = [
            {"id": 1, "amount": "not_a_float"},
        ]
        result = self.runner.run(records)
        self.assertEqual(result.quarantined, 1)
        self.assertEqual(result.loaded, 0)
        self.assertEqual(self.quarantine.count(), 1)


# ===========================================================================
# ConsoleAlerter tests
# ===========================================================================


class TestConsoleAlerter(unittest.TestCase):
    def _alerter(self) -> tuple[ConsoleAlerter, io.StringIO]:
        buf = io.StringIO()
        return ConsoleAlerter(stream=buf, use_colour=False), buf

    def test_alert_drift_detected(self) -> None:
        alerter, buf = self._alerter()
        events = [
            DriftEvent(
                column="name",
                drift_type=DriftType.COLUMN_REMOVED,
                old_type="str",
                new_type=None,
                severity="high",
            )
        ]
        alerter.alert_drift_detected("src", events)
        output = buf.getvalue()
        self.assertIn("DRIFT DETECTED", output)
        self.assertIn("name", output)

    def test_alert_healing_applied(self) -> None:
        alerter, buf = self._alerter()
        alerter.alert_healing_applied("src", "backfill", 3)
        self.assertIn("HEALED", buf.getvalue())
        self.assertIn("backfill", buf.getvalue())

    def test_alert_quarantine(self) -> None:
        alerter, buf = self._alerter()
        alerter.alert_quarantine("src", 2, "heal_failed")
        self.assertIn("QUARANTINE", buf.getvalue())
        self.assertIn("heal_failed", buf.getvalue())

    def test_alert_run_complete(self) -> None:
        alerter, buf = self._alerter()
        result = RunResult(loaded=10, quarantined=1, healed=5)
        alerter.alert_run_complete("src", result)
        out = buf.getvalue()
        self.assertIn("RUN COMPLETE", out)
        self.assertIn("loaded=10", out)


# ===========================================================================
# CLI tests
# ===========================================================================


class TestCLIDemo(unittest.TestCase):
    def test_demo_produces_output(self) -> None:
        import argparse  # noqa: PLC0415

        from selfheal.cli import cmd_demo  # noqa: PLC0415

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            ret = cmd_demo(argparse.Namespace())
        self.assertEqual(ret, 0)
        out = buf.getvalue()
        self.assertIn("demo", out.lower())
        self.assertIn("Batch 1", out)
        self.assertIn("Batch 2", out)
        self.assertIn("Batch 3", out)

    def test_demo_shows_schema_history(self) -> None:
        import argparse  # noqa: PLC0415

        from selfheal.cli import cmd_demo  # noqa: PLC0415

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            cmd_demo(argparse.Namespace())
        self.assertIn("Schema history", buf.getvalue())


class TestCLIRun(unittest.TestCase):
    def _run_cli(self, jsonl_input: str) -> tuple[int, str]:
        """Execute cmd_run with patched stdin, capture stdout."""
        import argparse  # noqa: PLC0415

        from selfheal.cli import cmd_run  # noqa: PLC0415

        stdin_mock = io.StringIO(jsonl_input)
        stdout_mock = io.StringIO()
        ns = argparse.Namespace(source="test_src", input="-")

        with patch("sys.stdin", stdin_mock), patch("sys.stdout", stdout_mock):
            ret = cmd_run(ns)
        return ret, stdout_mock.getvalue()

    def test_run_processes_valid_jsonl(self) -> None:
        lines = "\n".join([json.dumps({"id": i, "val": float(i)}) for i in range(3)])
        ret, out = self._run_cli(lines)
        self.assertEqual(ret, 0)
        data = json.loads(out)
        self.assertEqual(data["loaded"], 3)

    def test_run_skips_blank_lines(self) -> None:
        jsonl = '\n{"id": 1, "val": 1.0}\n\n{"id": 2, "val": 2.0}\n'
        ret, out = self._run_cli(jsonl)
        self.assertEqual(ret, 0)
        data = json.loads(out)
        self.assertEqual(data["loaded"], 2)

    def test_run_empty_stdin(self) -> None:
        ret, out = self._run_cli("")
        self.assertEqual(ret, 0)
        data = json.loads(out)
        self.assertEqual(data["loaded"], 0)


class TestCLIStatus(unittest.TestCase):
    def test_status_missing_file(self) -> None:
        import argparse  # noqa: PLC0415

        from selfheal.cli import cmd_status  # noqa: PLC0415

        ns = argparse.Namespace(registry_file="/tmp/no_such_file_selfheal_test.json")
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            ret = cmd_status(ns)
        self.assertEqual(ret, 1)

    def test_status_valid_registry(self, tmp_path: str | None = None) -> None:
        import argparse  # noqa: PLC0415
        import pathlib  # noqa: PLC0415

        from selfheal.cli import cmd_status  # noqa: PLC0415

        reg = SchemaRegistry()
        reg.register("s1", {"id": "int"})
        tmp = pathlib.Path("/tmp/selfheal_test_registry.json")
        tmp.write_text(reg.to_json())
        ns = argparse.Namespace(registry_file=str(tmp))
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            ret = cmd_status(ns)
        self.assertEqual(ret, 0)
        self.assertIn("s1", buf.getvalue())
        tmp.unlink(missing_ok=True)


# ===========================================================================
# Hypothesis property tests
# ===========================================================================

_schema_strategy = st.dictionaries(
    keys=st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"),
        min_size=1,
        max_size=20,
    ).filter(lambda s: s[0].isalpha()),
    values=st.sampled_from(["int", "float", "str", "bool"]),
    min_size=0,
    max_size=10,
)


class TestHypothesisProperties(unittest.TestCase):
    @given(_schema_strategy)
    @settings(max_examples=50)
    def test_schema_registry_roundtrip(self, schema: dict[str, str]) -> None:
        """Registering then serialising/deserialising a schema preserves it."""
        reg = SchemaRegistry()
        reg.register("source", schema)
        raw = reg.to_json()
        reg2 = SchemaRegistry.from_json(raw)
        active = reg2.get_active("source")
        self.assertIsNotNone(active)
        assert active is not None
        self.assertEqual(active.schema, schema)

    @given(_schema_strategy, _schema_strategy)
    @settings(max_examples=50)
    def test_drift_detect_added_cols_are_batch_minus_registered(
        self, registered: dict[str, str], extra: dict[str, str]
    ) -> None:
        """Columns in batch but not in registered schema → COLUMN_ADDED events."""
        # Remove any overlap from extra to isolate "purely new" columns
        pure_extra = {k: v for k, v in extra.items() if k not in registered}
        batch = {**registered, **pure_extra}
        events = DriftDetector(registered).detect(batch)
        added_cols = {e.column for e in events if e.drift_type == DriftType.COLUMN_ADDED}
        self.assertEqual(added_cols, set(pure_extra.keys()))

    @given(_schema_strategy, _schema_strategy)
    @settings(max_examples=50)
    def test_drift_detect_removed_cols_are_registered_minus_batch(
        self, base: dict[str, str], extra: dict[str, str]
    ) -> None:
        """Columns in registered but absent from batch → COLUMN_REMOVED events."""
        # Ensure 'extra' keys are truly absent from batch (not overlapping with base)
        pure_extra = {k: v for k, v in extra.items() if k not in base}
        registered = {**base, **pure_extra}
        batch = dict(base)
        events = DriftDetector(registered).detect(batch)
        removed_cols = {e.column for e in events if e.drift_type == DriftType.COLUMN_REMOVED}
        self.assertEqual(removed_cols, set(pure_extra.keys()))

    @given(
        st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.integers(0, 100),
                    "amount": st.floats(0.0, 1000.0, allow_nan=False, allow_infinity=False),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=50)
    def test_infer_schema_always_returns_consistent_types(
        self, records: list[dict[str, object]]
    ) -> None:
        """infer_schema always produces a non-empty schema for non-empty input."""
        schema = DriftDetector.infer_schema(records)
        self.assertIn("id", schema)
        self.assertIn("amount", schema)
        self.assertEqual(schema["id"], "int")
        # floats from hypothesis might infer as "float"
        self.assertIn(schema["amount"], ("float", "int"))


if __name__ == "__main__":
    unittest.main()
