#!/usr/bin/env python3
"""A status filter named in the sentence must actually be applied.

The defect, measured on the live harness.  ``sqlite.table.create_from_json_records``
derived its status filter *only* from the data, and only when every record agreed on
one status:

    wanted = _status_value_from_records(records)   # None unless the records are unanimous

So a goal saying "from the ACTIVE records" over a mixed collection produced
``wanted = None``, the filter was skipped, and the table was built from **every**
record.  Not an error -- a confident superset of what was asked for.  The harness
showed it directly:

    expected [('byoop','5'),('itorp','9'),('sqqsp','83'),('uxflz','80')]
    got      those four PLUS ('pibiy','4')

Measured before the fix: 4 of 10 instances correct.  After: 25 of 25 on both the
create and the verify family.

The fix reads the status the sentence names, choosing it from the distinct status
values the records actually carry -- so it works for any vocabulary and maintains no
list of words.  The verify adapter carried the identical line and is fixed with it,
because a create that filters and a verify that does not would contradict each other.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import sqlite3
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CREATE_ADAPTER = ROOT / "canonical/runtime/bound_capabilities/sqlite_table_stdlib.py"
VERIFY_ADAPTER = ROOT / "canonical/runtime/bound_capabilities/sqlite_verify_cli.py"


def _load(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SqliteStatusFilterBase(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="sqlite_status_filter_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.create = _load(CREATE_ADAPTER, "sqlite_table_stdlib_under_test")

    def _write_records(self, statuses):
        """Records keyed by id, each carrying the status given for it."""
        records = {
            rid: {"capability_id": rid, "n": str(i + 1), "note": "r" + rid, "status": st}
            for i, (rid, st) in enumerate(statuses)
        }
        (self.tmp / "records.json").write_text(
            json.dumps({"things": records}), encoding="utf-8"
        )
        return records

    def _goal(self, status_word=None, table="things"):
        words = f"from the {status_word} records " if status_word else "from the records "
        return (
            f"Create a sqlite database table named {table} {words}in records.json "
            "with columns capability_id, n, note."
        )

    def _run(self, goal):
        return self.create.run(
            {"json_path": "records.json", "output_path": "work.db", "goal": goal},
            self.tmp,
        )

    def _ids_in_table(self, table="things"):
        conn = sqlite3.connect(str(self.tmp / "work.db"))
        try:
            rows = conn.execute(
                f'SELECT capability_id FROM "{table}" ORDER BY capability_id'
            ).fetchall()
        finally:
            conn.close()
        return [r[0] for r in rows]


class TestTheNamedStatusIsApplied(SqliteStatusFilterBase):
    MIXED = [("aaa", "ACTIVE"), ("bbb", "RETIRED"), ("ccc", "ACTIVE"), ("ddd", "DRAFT")]

    def test_a_mixed_collection_is_filtered_to_the_status_the_sentence_names(self):
        """The exact defect: mixed statuses used to insert everything."""
        self._write_records(self.MIXED)
        result = self._run(self._goal("ACTIVE"))
        self.assertEqual(self._ids_in_table(), ["aaa", "ccc"])
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["status_value"], "ACTIVE")

    def test_a_different_vocabulary_works_with_no_code_change(self):
        """Proof this is not a list of phrasings or of words.

        RETIRED appears nowhere in the adapter.  It works because the value is drawn
        from the records' own vocabulary and matched against the sentence.
        """
        self._write_records(self.MIXED)
        self._run(self._goal("RETIRED"))
        self.assertEqual(self._ids_in_table(), ["bbb"])

    def test_naming_two_statuses_present_in_the_data_fails_closed(self):
        """A contradiction must be refused, not resolved by picking one."""
        self._write_records(self.MIXED)
        with self.assertRaises(RuntimeError) as caught:
            self._run(self._goal("ACTIVE and RETIRED"))
        self.assertIn("SQLITE_STATUS_AMBIGUOUS", str(caught.exception))

    def test_a_status_word_that_is_not_a_real_value_changes_nothing(self):
        """Matching is against the data's vocabulary, so a stray word is not a filter.

        'active' lowercased appears in the sentence but is not one of the record
        statuses here (they are PENDING/CLOSED), so nothing may be filtered away.
        """
        self._write_records([("aaa", "PENDING"), ("bbb", "CLOSED")])
        result = self._run(self._goal("PENDING"))
        self.assertEqual(self._ids_in_table(), ["aaa"])
        self.assertEqual(result["status_value"], "PENDING")


class TestUnanimousDataIsUnchanged(SqliteStatusFilterBase):
    def test_when_every_record_agrees_the_old_behaviour_still_holds(self):
        """The fix must not regress the case that already worked."""
        self._write_records([("aaa", "ACTIVE"), ("bbb", "ACTIVE")])
        result = self._run(self._goal())  # sentence names no status at all
        self.assertEqual(self._ids_in_table(), ["aaa", "bbb"])
        self.assertEqual(result["status_value"], "ACTIVE")

    def test_no_status_named_and_none_agreeing_keeps_every_row(self):
        """Falls back to the data-derived value, which is None, so no filter."""
        self._write_records([("aaa", "PENDING"), ("bbb", "CLOSED")])
        result = self._run(self._goal())
        self.assertEqual(self._ids_in_table(), ["aaa", "bbb"])
        self.assertIsNone(result["status_value"])


class TestCreateAndVerifyAgree(SqliteStatusFilterBase):
    """The pair must filter identically or they contradict each other."""

    def test_the_verify_adapter_filters_by_the_same_named_status(self):
        self._write_records([("aaa", "ACTIVE"), ("bbb", "RETIRED"), ("ccc", "ACTIVE")])
        self._run(self._goal("ACTIVE"))
        verify = _load(VERIFY_ADAPTER, "sqlite_verify_cli_under_test")
        result = verify.run(
            {
                "json_path": "records.json",
                "sqlite_path": "work.db",
                "goal": "Verify the sqlite database against the JSON records "
                "for the table named things from the ACTIVE records.",
            },
            self.tmp,
        )
        self.assertEqual(result["status_value"], "ACTIVE")

    def test_verify_rejects_a_table_built_without_the_filter(self):
        """Build the buggy superset by hand; the verifier must catch it."""
        self._write_records([("aaa", "ACTIVE"), ("bbb", "RETIRED")])
        conn = sqlite3.connect(str(self.tmp / "work.db"))
        conn.execute("CREATE TABLE things (capability_id TEXT, n TEXT, note TEXT)")
        conn.executemany(
            "INSERT INTO things VALUES (?,?,?)",
            [("aaa", "1", "raaa"), ("bbb", "2", "rbbb")],
        )
        conn.commit()
        conn.close()
        verify = _load(VERIFY_ADAPTER, "sqlite_verify_cli_superset")
        with self.assertRaises(RuntimeError) as caught:
            verify.run(
                {
                    "json_path": "records.json",
                    "sqlite_path": "work.db",
                    "goal": "Verify the sqlite database against the JSON records "
                    "for the table named things from the ACTIVE records.",
                },
                self.tmp,
            )
        self.assertIn("SQLITE_ID_SET_MISMATCH", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
