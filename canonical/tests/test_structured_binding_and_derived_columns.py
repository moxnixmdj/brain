"""Columns come from the records; a structured slot binds a file that has them.

Two defects that were each invisible alone and only visible together, measured
on "Create an xlsx table from JSON records.":

1. ``xlsx_table_xlsxwriter._columns`` demanded the sentence state the columns,
   raising ``XLSX_COLUMNS_UNRESOLVED``. But a record collection's keys ARE its
   columns -- the data states them.
2. ``world_binding_v1._world_path_for`` returned the first alphabetically
   sorted match, which for ``json_path`` was ``MIGRATION_STATUS_2026-09-10.json``
   -- a flat status document holding no records at all.

Fixing either alone moved nothing: derived columns had no records to read, and
a file full of records had no columns to use. Fixing both took that goal from
blocked to passing end to end.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOUND = ROOT / "runtime" / "bound_capabilities"


def _load(name):
    """Load an adapter by path without touching sys.modules.

    These adapters import nothing of each other, so no registration is needed,
    and the repository integrity guard rejects replacing a real module with a
    stand-in.
    """
    spec = importlib.util.spec_from_file_location(name, BOUND / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestColumnsDerivedFromRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.xa = _load("xlsx_table_xlsxwriter")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = pathlib.Path(cls.tmp.name)
        records = {"rows": {"a": {"id": 1, "text": "x"}, "b": {"id": 2, "text": "y"}}}
        cls.with_records = cls.root / "records.json"
        cls.with_records.write_text(json.dumps(records), encoding="utf-8")
        cls.recordless = cls.root / "flat.json"
        cls.recordless.write_text(
            json.dumps({"title": "status", "updated": "2026-09-10"}), encoding="utf-8"
        )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _run(self, json_name, goal):
        out = self.root / "out.xlsx"
        if out.exists():
            out.unlink()
        return self.xa.run(
            {"json_path": json_name, "output_path": "out.xlsx", "goal": goal},
            str(self.root),
        )

    def test_a_silent_sentence_still_yields_the_columns_the_data_states(self):
        result = self._run("records.json", "Create an xlsx table from JSON records.")
        self.assertEqual(result["columns"], ["id", "text"])
        self.assertEqual(result["row_count"], 2)
        self.assertTrue(result["output_verified"])

    def test_derivation_is_deterministic_and_sorted(self):
        first = self._run("records.json", "Create an xlsx table from JSON records.")
        second = self._run("records.json", "Create an xlsx table from JSON records.")
        self.assertEqual(first["columns"], second["columns"])
        self.assertEqual(first["output_sha256"], second["output_sha256"])

    def test_an_explicit_but_invalid_column_list_still_raises(self):
        """Derivation must not quietly override a stated intent."""
        with self.assertRaises(RuntimeError) as ctx:
            self._run("records.json", "Create an xlsx table with columns id, id.")
        self.assertEqual(str(ctx.exception), "XLSX_COLUMNS_DUPLICATE")

    def test_a_stated_column_list_still_wins_over_derivation(self):
        result = self._run("records.json", "Create an xlsx table with columns text.")
        self.assertEqual(result["columns"], ["text"])

    def test_a_document_with_no_records_still_fails_closed(self):
        """No records means no honest columns; inventing a header is worse."""
        with self.assertRaises(RuntimeError) as ctx:
            self._run("flat.json", "Create an xlsx table from JSON records.")
        self.assertEqual(str(ctx.exception), "XLSX_COLUMNS_UNRESOLVED")


class TestStructuredBindingPrefersAFileWithRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Loaded by path, not registered: world_binding_v1 resolves
        # canonical.runtime.world_probe_v1 through the normal import system,
        # which works because the repository root is importable.
        spec = importlib.util.spec_from_file_location(
            "wb_probe", ROOT / "runtime" / "world_binding_v1.py"
        )
        cls.wb = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.wb)

    def test_the_predicate_accepts_both_record_shapes_the_adapters_accept(self):
        self.assertTrue(self.wb._is_record_collection({"a": {"x": 1}, "b": {"x": 2}}))
        self.assertTrue(self.wb._is_record_collection([{"x": 1}, {"x": 2}]))
        self.assertTrue(self.wb._is_record_collection({"wrap": {"a": {"x": 1}}}))

    def test_the_predicate_rejects_a_flat_status_document(self):
        """This is exactly the shape that used to win on alphabetical order."""
        self.assertFalse(self.wb._is_record_collection(
            {"title": "status", "updated": "2026-09-10", "count": 3}
        ))
        self.assertFalse(self.wb._is_record_collection({}))
        self.assertFalse(self.wb._is_record_collection("text"))

    def test_the_scan_finds_the_first_file_with_records_and_skips_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "a_flat.json").write_text(json.dumps({"k": "v"}), encoding="utf-8")
            (root / "b_flat.json").write_text(json.dumps({"k2": "v2"}), encoding="utf-8")
            (root / "c_records.json").write_text(
                json.dumps({"r": {"id": 1}}), encoding="utf-8"
            )
            ordered = ["a_flat.json", "b_flat.json", "c_records.json"]
            self.assertEqual(
                self.wb._first_with_records(ordered, root), "c_records.json"
            )

    def test_the_scan_returns_none_when_nothing_qualifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "a_flat.json").write_text(json.dumps({"k": "v"}), encoding="utf-8")
            self.assertIsNone(self.wb._first_with_records(["a_flat.json"], root))


if __name__ == "__main__":
    unittest.main()
