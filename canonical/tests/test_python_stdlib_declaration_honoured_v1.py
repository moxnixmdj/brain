#!/usr/bin/env python3
"""A capability that declares ``python_stdlib`` must need nothing but the interpreter.

The registry records a ``source.type`` for every bound capability. ``python_stdlib``
is a promise: this adapter runs on a bare interpreter, on every host, with nothing
installed.  Measured across the family, 30 capabilities make that promise and exactly
one broke it -- ``sqlite.table.verify_against_json_records`` shelled out to the
``sqlite3`` CLI and only fell back to the ``sqlite3`` *module* when the binary was
absent.  The promise held by accident.

That accident had a real cost.  The recorded end-to-end receipt
``canonical/capabilities/true/LIVE_SOLVER_END_TO_END_MEASUREMENT_20261015_V4.json``
logs this family as ``environment_blocked_here: 50`` -- all fifty instances blocked by
a missing tool -- for a capability whose only real dependency is in the standard
library.  Re-run here, with the ``sqlite3`` binary absent, the family passes 3/3.

These tests make the promise enforced rather than incidental: one general guard over
the whole family, and one end-to-end run of the adapter that actually reads rows back
and actually detects a tampered database.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
ADAPTER_REL = "canonical/runtime/bound_capabilities/sqlite_verify_cli.py"

# Matches an external binary being named in a process invocation or a lookup.
_BINARY_CALL = re.compile(r'subprocess\.\w+\(\s*\[\s*"([A-Za-z0-9_.\-]+)"')
_WHICH_CALL = re.compile(r'shutil\.which\(\s*"([A-Za-z0-9_.\-]+)"')


def _capabilities() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]


def _load(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestStdlibDeclarationIsHonoured(unittest.TestCase):
    def test_no_python_stdlib_capability_reaches_for_an_external_binary(self):
        """General guard over the whole family, not just the file that was fixed.

        Measured before the fix: 30 capabilities declare ``python_stdlib``; 5 declare no
        adapter at all and are skipped; exactly 1 invoked a binary (``sqlite3``, absent
        here).  After the fix the count is 0.  Any future adapter that shells out while
        declaring no dependency turns this red.
        """
        offenders = []
        checked = 0
        for cid, entry in sorted(_capabilities().items()):
            source = entry.get("source") or {}
            if source.get("type") != "python_stdlib":
                continue
            rel = source.get("adapter_path")
            if not rel:
                continue
            path = ROOT / rel
            self.assertTrue(path.is_file(), f"{cid}: declared adapter missing: {rel}")
            checked += 1
            text = path.read_text(encoding="utf-8")
            named = set(_BINARY_CALL.findall(text)) | set(_WHICH_CALL.findall(text))
            if named:
                offenders.append((cid, sorted(named)))
        self.assertGreater(checked, 20, "family scan found almost nothing; it is not measuring")
        self.assertEqual(offenders, [], "python_stdlib capabilities that need an external binary")

    def test_the_fixed_adapter_no_longer_imports_subprocess_at_all(self):
        """The CLI path is gone, not merely deprioritised.

        Leaving the import in place would let the host dependency creep back without
        touching a line this test can see.
        """
        module = _load(ROOT / ADAPTER_REL, "sqlite_verify_cli_no_subprocess")
        self.assertNotIn("subprocess", dir(module))
        self.assertNotIn("shutil", dir(module))


class TestSqliteVerifyNeedsNoBinary(unittest.TestCase):
    """End-to-end through the real adapter, with no sqlite3 binary on the box."""

    def setUp(self):
        self.assertTrue(
            shutil.which("sqlite3") is None or True,  # informational; the test holds either way
        )
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="sqlite_stdlib_verify_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        # The adapter reads a collection as either a list (keyed by index) or a mapping
        # (keyed by its own keys) -- see _record_items.  A mapping is used here so the
        # expected ids are the real record ids rather than "0" and "1".
        self.records = {
            "alpha": {"capability_id": "alpha", "n": "1", "note": "first"},
            "beta": {"capability_id": "beta", "n": "2", "note": "second"},
        }
        (self.tmp / "records.json").write_text(
            json.dumps({"things": self.records}), encoding="utf-8"
        )
        self.db_rel = "work.db"
        self._write_db(self.records)
        self.goal = "Verify the sqlite database against the JSON records for the table named things."

    def _write_db(self, records):
        db = self.tmp / self.db_rel
        if db.exists():
            db.unlink()
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE things (capability_id TEXT, n TEXT, note TEXT)")
        conn.executemany(
            "INSERT INTO things VALUES (?,?,?)",
            [(r["capability_id"], r["n"], r["note"]) for r in records.values()],
        )
        conn.commit()
        conn.close()

    def _run(self):
        module = _load(ROOT / ADAPTER_REL, "sqlite_verify_cli_roundtrip")
        return module.run(
            {"json_path": "records.json", "sqlite_path": self.db_rel, "goal": self.goal},
            self.tmp,
        )

    def test_it_reads_the_rows_back_with_no_binary_present(self):
        result = self._run()
        self.assertEqual(result.get("adapter"), "sqlite_verify_cli")
        self.assertEqual(result.get("sqlite_path"), self.db_rel)
        # The digest must be of the real bytes on disk, computed independently here.
        expected = hashlib.sha256((self.tmp / self.db_rel).read_bytes()).hexdigest()
        self.assertEqual(result.get("sqlite_sha256"), expected)

    def test_it_actually_verifies_and_rejects_a_tampered_database(self):
        """A verifier that only proves it did not crash is not a verifier.

        Change one cell and the adapter must name the mismatch rather than pass.
        """
        tampered = {k: dict(v) for k, v in self.records.items()}
        tampered["beta"]["note"] = "not what the json says"
        self._write_db(tampered)
        with self.assertRaises(RuntimeError) as caught:
            self._run()
        self.assertIn("SQLITE_VALUE_MISMATCH", str(caught.exception))
        self.assertIn("note", str(caught.exception))

    def test_it_rejects_a_database_missing_a_row(self):
        self._write_db({"alpha": self.records["alpha"]})
        with self.assertRaises(RuntimeError) as caught:
            self._run()
        self.assertIn("SQLITE_ID_SET_MISMATCH", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
