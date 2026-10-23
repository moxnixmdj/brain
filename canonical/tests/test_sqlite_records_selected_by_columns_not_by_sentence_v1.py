"""A sqlite table can be verified against JSON records the sentence never described.

`sqlite_verify_cli` and `sqlite_table_stdlib` both resolved their source collection by
scanning the goal sentence for an UPPERCASE token and demanding that token appear as a value
in the JSON. A sentence without one -- "Verify a sqlite table against JSON records." -- raised
`SQLITE_STATUS_VALUE_UNRESOLVED` before it ever looked at the data.

The sibling family already solved this. `xlsx_verify_openpyxl` and `xlsx_table_xlsxwriter`
select their source with `_select_collection(data, columns)`: the collection whose records can
actually supply the columns the work needs, shallowest first, failing closed when the shallowest
survivors are not exactly one. And they derive the status with
`_status_value_from_records(records)` -- exactly one distinct value is a fact about the
document; anything else declines to filter.

Those three helpers are ported here verbatim in behaviour, so the two families now resolve
their source the same way. The dead `_status_value` / `_find_collection` pair is deleted from
both adapters rather than left as a trap.

What this does NOT do: it does not invent a status, and it does not make an under-specified
goal pass. When no collection can supply the columns the answer is
`SQLITE_RECORD_COLLECTION_NOT_FOUND`, and when two collections could the answer is
`SQLITE_RECORD_COLLECTION_AMBIGUOUS` with both paths named. Measured on the benchmark goal
`EXT_SQLITE_VERIFY`: the binder hands this adapter `canonical/CANONICAL_POINTER.json` -- a
governance pointer document, not a table of records -- so that goal still fails, and now says
precisely why instead of blaming a status token nobody ever needed to state.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sqlite3
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TMP = REPO_ROOT / "canonical" / "astra_runtime" / "tmp"
HERE = "canonical/astra_runtime/tmp"


def _load(name):
    import importlib.util
    path = REPO_ROOT / "canonical/runtime/bound_capabilities" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify_cli = _load("sqlite_verify_cli")
table_stdlib = _load("sqlite_table_stdlib")

# Two records that agree on one status, and columns both can supply.
RECORDS = {
    "alpha.one": {"capability_id": "alpha.one", "status": "VERIFIED", "cost": "1"},
    "beta.two": {"capability_id": "beta.two", "status": "VERIFIED", "cost": "2"},
}


class _Fixture(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True, exist_ok=True)
        self._made = []

    def _require_cli(self):
        """Only `sqlite_verify_cli` shells out to the sqlite3 binary; the create-side adapter
        and every resolution helper use the stdlib module, so those tests must still run on a
        host without the CLI rather than silently skipping the whole file."""
        if shutil.which("sqlite3") is None:
            self.skipTest("the sqlite3 CLI is not installed on this host")

    def _write(self, name, payload):
        path = TMP / name
        path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
        self._made.append(path)
        return (HERE + "/" + name)

    def tearDown(self):
        for path in self._made:
            path.unlink(missing_ok=True)


class CreateThenVerifyRoundtripTests(_Fixture):
    """The capability gain: neither sentence states a status, and both now work."""

    def test_a_table_can_be_created_from_records_the_sentence_never_described(self):
        json_rel = self._write("RT_RECORDS.json", {"capabilities": RECORDS})
        out_rel = HERE + "/RT_TABLE.sqlite"
        self._made.append(REPO_ROOT / out_rel)
        result = table_stdlib.run({
            "goal": "Create a sqlite table named capabilities with columns capability_id, "
                    "status and cost.",
            "json_path": json_rel,
            "output_path": out_rel,
        }, REPO_ROOT)
        self.assertEqual(result.get("row_count"), 2, result)
        rows = sqlite3.connect(str(REPO_ROOT / out_rel)).execute(
            'SELECT capability_id FROM "capabilities" ORDER BY capability_id').fetchall()
        self.assertEqual([r[0] for r in rows], ["alpha.one", "beta.two"])

    def test_it_can_then_be_verified_against_the_same_records(self):
        self._require_cli()
        json_rel = self._write("RT_RECORDS.json", {"capabilities": RECORDS})
        out_rel = HERE + "/RT_TABLE.sqlite"
        self._made.append(REPO_ROOT / out_rel)
        table_stdlib.run({
            "goal": "Create a sqlite table named capabilities with columns capability_id, "
                    "status and cost.",
            "json_path": json_rel, "output_path": out_rel}, REPO_ROOT)
        result = verify_cli.run({
            "goal": "Verify a sqlite table against JSON records.",
            "json_path": json_rel, "sqlite_path": out_rel}, REPO_ROOT)
        self.assertIs(result.get("verified"), True, result)

    def test_the_table_name_is_still_taken_from_the_sentence_when_it_states_one(self):
        json_rel = self._write("RT_RECORDS.json", {"capabilities": RECORDS})
        out_rel = HERE + "/RT_NAMED.sqlite"
        self._made.append(REPO_ROOT / out_rel)
        table_stdlib.run({
            "goal": "Create a sqlite table named widgets with columns capability_id, status and cost.",
            "json_path": json_rel, "output_path": out_rel}, REPO_ROOT)
        names = [r[0] for r in sqlite3.connect(str(REPO_ROOT / out_rel)).execute(
            "SELECT name FROM sqlite_master WHERE type='table'")]
        self.assertEqual(names, ["widgets"])


class CreatingNeedsANameButVerifyingDoesNotTests(_Fixture):
    """The asymmetry is deliberate and worth pinning.

    A table cannot be created without a name -- there is nothing to derive one from.  A table
    that already exists CAN: `sqlite_master` says what it is called, and if it says more than
    one thing the verify adapter fails closed instead of choosing.  So the create adapter
    refuses an unnamed table and the verify adapter does not, and neither invents a name.
    """

    def test_creating_without_a_name_is_refused_rather_than_invented(self):
        json_rel = self._write("RT_RECORDS.json", {"capabilities": dict(RECORDS)})
        out_rel = HERE + "/RT_UNNAMED.sqlite"
        self._made.append(REPO_ROOT / out_rel)
        with self.assertRaises(RuntimeError) as ctx:
            table_stdlib.run({
                "goal": "Create a sqlite table with columns capability_id, status and cost.",
                "json_path": json_rel, "output_path": out_rel}, REPO_ROOT)
        self.assertIn("SQLITE_TABLE_NAME_UNRESOLVED", str(ctx.exception))
        self.assertFalse((REPO_ROOT / out_rel).exists(),
                         "it refused but still created something")

    def test_verifying_derives_the_single_table_from_the_database_itself(self):
        self._require_cli()
        json_rel = self._write("RT_RECORDS.json", {"capabilities": dict(RECORDS)})
        out_rel = HERE + "/RT_DERIVE.sqlite"
        self._made.append(REPO_ROOT / out_rel)
        table_stdlib.run({
            "goal": "Create a sqlite table named widgets with columns capability_id, "
                    "status and cost.",
            "json_path": json_rel, "output_path": out_rel}, REPO_ROOT)
        result = verify_cli.run({"goal": "Verify a sqlite table against JSON records.",
                                 "json_path": json_rel, "sqlite_path": out_rel}, REPO_ROOT)
        self.assertIs(result.get("verified"), True, result)


class VerificationStillCatchesALieTests(_Fixture):
    """The point of the capability. A green check that cannot go red proves nothing."""

    def _roundtrip(self):
        self._require_cli()
        json_rel = self._write("RT_RECORDS.json", {"capabilities": dict(RECORDS)})
        out_rel = HERE + "/RT_LIE.sqlite"
        self._made.append(REPO_ROOT / out_rel)
        table_stdlib.run({
            "goal": "Create a sqlite table named capabilities with columns capability_id, "
                    "status and cost.",
            "json_path": json_rel, "output_path": out_rel}, REPO_ROOT)
        return json_rel, out_rel

    def test_a_changed_cell_is_detected(self):
        json_rel, out_rel = self._roundtrip()
        conn = sqlite3.connect(str(REPO_ROOT / out_rel))
        conn.execute("UPDATE capabilities SET cost='999' WHERE capability_id='alpha.one'")
        conn.commit(); conn.close()
        with self.assertRaises(RuntimeError) as ctx:
            verify_cli.run({"goal": "Verify a sqlite table against JSON records.",
                            "json_path": json_rel, "sqlite_path": out_rel}, REPO_ROOT)
        self.assertIn("SQLITE_", str(ctx.exception))

    def test_a_deleted_row_is_detected(self):
        json_rel, out_rel = self._roundtrip()
        conn = sqlite3.connect(str(REPO_ROOT / out_rel))
        conn.execute("DELETE FROM capabilities WHERE capability_id='beta.two'")
        conn.commit(); conn.close()
        with self.assertRaises(RuntimeError) as ctx:
            verify_cli.run({"goal": "Verify a sqlite table against JSON records.",
                            "json_path": json_rel, "sqlite_path": out_rel}, REPO_ROOT)
        self.assertIn("SQLITE_ID_SET_MISMATCH", str(ctx.exception))

    def test_a_forged_matching_table_still_has_to_match_the_records(self):
        """Verification is against the JSON, not against itself."""
        self._require_cli()
        json_rel = self._write("RT_RECORDS.json", {"capabilities": dict(RECORDS)})
        out_rel = HERE + "/RT_FORGED.sqlite"
        self._made.append(REPO_ROOT / out_rel)
        conn = sqlite3.connect(str(REPO_ROOT / out_rel))
        conn.execute('CREATE TABLE capabilities (capability_id TEXT, status TEXT, cost TEXT)')
        conn.execute("INSERT INTO capabilities VALUES ('alpha.one','VERIFIED','1')")
        conn.commit(); conn.close()
        with self.assertRaises(RuntimeError) as ctx:
            verify_cli.run({"goal": "Verify a sqlite table against JSON records.",
                            "json_path": json_rel, "sqlite_path": out_rel}, REPO_ROOT)
        self.assertIn("SQLITE_ID_SET_MISMATCH", str(ctx.exception))


class DecliningToGuessTests(_Fixture):
    """Where the data cannot answer, the adapter must say so and name what it saw."""

    def test_a_document_with_no_matching_collection_is_refused(self):
        """A governance pointer document is not a table of records, and must not be read as one.

        This is the exact shape the binder hands the benchmark goal EXT_SQLITE_VERIFY, so it is
        pinned as a pure-function test: it runs on every host, CLI or not.
        """
        pointer = {"active_pointer": {"path": "canonical/x.json", "sha256": "0" * 64},
                   "schema": "PROJECT_BRAIN_CANONICAL_POINTER_V1"}
        with self.assertRaises(RuntimeError) as ctx:
            verify_cli._select_collection(pointer, ["capability_id", "status", "cost"])
        self.assertIn("SQLITE_RECORD_COLLECTION_NOT_FOUND", str(ctx.exception))

    def test_two_equally_shallow_collections_are_refused_as_ambiguous(self):
        """Never pick one. Both paths are named so the caller can disambiguate."""
        payload = {"left": {"capabilities": dict(RECORDS)},
                   "right": {"capabilities": dict(RECORDS)}}
        with self.assertRaises(RuntimeError) as ctx:
            verify_cli._select_collection(payload, ["capability_id", "status", "cost"])
        message = str(ctx.exception)
        self.assertIn("SQLITE_RECORD_COLLECTION_AMBIGUOUS", message)
        self.assertIn("left", message)
        self.assertIn("right", message)

    def test_records_disagreeing_on_status_are_not_filtered_at_all(self):
        """Exactly one status is a fact; two is a choice, and it declines to make it."""
        mixed = {
            "alpha.one": {"capability_id": "alpha.one", "status": "VERIFIED", "cost": "1"},
            "beta.two": {"capability_id": "beta.two", "status": "REJECTED", "cost": "2"},
        }
        self.assertIsNone(verify_cli._status_value_from_records(mixed))
        self.assertEqual(verify_cli._status_value_from_records(dict(RECORDS)), "VERIFIED")

    def test_a_list_of_records_is_understood_as_well_as_a_mapping(self):
        payload = [{"capability_id": "alpha.one", "status": "VERIFIED", "cost": "1"}]
        self.assertEqual(len(verify_cli._record_items(payload)), 1)
        path, node = verify_cli._select_collection(
            payload, ["capability_id", "status", "cost"])
        self.assertEqual(list(path), [])
        self.assertEqual(node, payload)


class TheTwoAdaptersAgreeTests(unittest.TestCase):
    """One family, one resolution rule -- the half-fixed family is the failure mode."""

    def test_both_select_their_collection_the_same_way(self):
        for module in (verify_cli, table_stdlib):
            with self.subTest(adapter=module.__name__):
                self.assertTrue(hasattr(module, "_select_collection"))
                self.assertTrue(hasattr(module, "_status_value_from_records"))
                self.assertFalse(hasattr(module, "_status_value"),
                                 "the goal-token predicate is still present")

    def test_neither_can_refuse_on_a_missing_status_token_any_more(self):
        for module in (verify_cli, table_stdlib):
            with self.subTest(adapter=module.__name__):
                source = (REPO_ROOT / "canonical/runtime/bound_capabilities"
                          / (module.__name__ + ".py")).read_text(encoding="utf-8")
                self.assertNotIn("raise RuntimeError(\"SQLITE_STATUS_VALUE_UNRESOLVED\")", source)


if __name__ == "__main__":
    unittest.main()
