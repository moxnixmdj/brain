"""The sqlite verifier's declared substrate is Python's own sqlite3 module.

`sqlite.table.verify_against_json_records` was declared as an Ubuntu apt
package, so on a host without the `sqlite3` CLI the substrate gate raised
`BOUND_APT_METADATA_NOT_FOUND:sqlite3` and the capability never ran at all.

That declaration described a preference, not a requirement. The adapter shells
out to the CLI and, on `FileNotFoundError`, imports the stdlib module instead
-- and its own registry entry already said so, carrying `"optional": true`, a
`"fallback": {"type":"python_stdlib","module":"sqlite3"}` and an
`optional_reason` naming the adapter. The gate read none of those fields.

So the declaration was corrected to what the code does, mirroring the sibling
capability `sqlite.table.create_from_json_records`, which has always been
declared `python_stdlib` and has always worked here.

Measured after the change, on a host with no `sqlite3` binary: the failure
moves off the substrate gate entirely and into row comparison
(`SQLITE_COLUMN_UNRESOLVED:source_type`), which means the table and its schema
were read through Python's `sqlite3`. A capability that could not run now runs
and answers about the data instead of about the host.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

import sys

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import astra_runtime  # noqa: E402

Blocker = astra_runtime.Blocker
REGISTRY = REPO_ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
CID = "sqlite.table.verify_against_json_records"
SIBLING = "sqlite.table.create_from_json_records"


def _entry(cid):
    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return doc["capabilities"][cid]


class DeclaredSubstrateTests(unittest.TestCase):
    def test_the_verifier_declares_the_stdlib_module_not_an_apt_package(self):
        source = _entry(CID).get("source") or {}
        self.assertEqual(source.get("type"), "python_stdlib")
        self.assertEqual(source.get("module"), "sqlite3")
        self.assertNotIn("packages", source)
        self.assertEqual(
            source.get("adapter_path"),
            "canonical/runtime/bound_capabilities/sqlite_verify_cli.py",
        )

    def test_it_is_declared_the_same_way_as_the_sibling_that_always_worked(self):
        """The create capability has been python_stdlib:sqlite3 all along and
        has never been apt-blocked. Matching its shape is what makes this a
        correction rather than a new invention."""
        verifier = _entry(CID)["source"]
        sibling = _entry(SIBLING)["source"]
        self.assertEqual(sorted(verifier), sorted(sibling))
        self.assertEqual(verifier["type"], sibling["type"])
        self.assertEqual(verifier["module"], sibling["module"])

    def test_the_adapter_really_does_fall_back_to_the_stdlib(self):
        """The declaration is a claim about the adapter, so read the adapter.
        Without this the change would let a capability run that cannot work."""
        text = (
            REPO_ROOT / "canonical/runtime/bound_capabilities/sqlite_verify_cli.py"
        ).read_text(encoding="utf-8")
        self.assertIn("except FileNotFoundError", text)
        self.assertIn("import sqlite3", text)


class GateAcceptsTheDeclarationTests(unittest.TestCase):
    def test_the_real_entry_passes_the_substrate_gate(self):
        """Through the real gate function, on the real registry entry."""
        out = astra_runtime._ensure_local_dependency(_entry(CID)["source"])
        self.assertEqual(out["status"], "LOCAL_VERIFIED")
        self.assertEqual(out["type"], "python_stdlib")
        self.assertIn("sqlite3", out["modules"])

    def test_a_python_stdlib_declaration_naming_a_missing_module_still_blocks(self):
        """Negative control. Declaring python_stdlib is not a way around the
        gate: the module is probed, and one that does not exist blocks."""
        with self.assertRaises(Blocker) as ctx:
            astra_runtime._ensure_local_dependency(
                {"type": "python_stdlib", "module": "no_such_module_anywhere"}
            )
        self.assertIn("BOUND_PYTHON_STDLIB_MODULE_MISSING", str(ctx.exception))

    def test_a_malformed_module_name_is_rejected(self):
        with self.assertRaises(Blocker):
            astra_runtime._ensure_local_dependency(
                {"type": "python_stdlib", "module": "os; rm -rf /"}
            )

    def test_an_empty_module_declaration_is_rejected(self):
        with self.assertRaises(Blocker):
            astra_runtime._ensure_local_dependency({"type": "python_stdlib"})


class CapabilityActuallyRunsTests(unittest.TestCase):
    """The point of the change: the capability reaches its own logic."""

    def test_the_substrate_blocker_is_gone(self):
        if shutil.which("sqlite3"):
            self.skipTest("sqlite3 CLI present; the fallback is not exercised")
        import sqlite3 as py_sqlite3

        from canonical.runtime import live_integrated_brain_v1 as live

        res = live.run_raw_goal(
            {"task_id": "SUBSTRATE_DECLARATION_PROBE",
             "goal": "Verify a sqlite table against JSON records."}
        )
        reason = str(res.get("reason") or "")
        status = str(res.get("status") or "")
        self.assertNotIn("BOUND_APT_METADATA_NOT_FOUND", reason + status)
        # And the stdlib really can do what the adapter needs done.
        tmp = REPO_ROOT / "canonical/astra_runtime/tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        db = tmp / "_substrate_declaration_probe.sqlite"
        conn = py_sqlite3.connect(str(db))
        try:
            conn.execute("CREATE TABLE t (capability_id TEXT, status TEXT)")
            conn.execute("INSERT INTO t VALUES ('a.b', 'VERIFIED_BOUND_CAPABILITY')")
            conn.commit()
            names = [
                r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
        finally:
            conn.close()
        self.addCleanup(db.unlink, True)
        self.assertIn("t", names)

    def test_no_other_entry_lost_its_apt_declaration(self):
        """Scope guard. Exactly one entry changed; every other apt-declared
        capability keeps the hash-pinned claim it had."""
        doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
        apt = [
            cid for cid, e in doc["capabilities"].items()
            if (e.get("source") or {}).get("type") == "apt"
        ]
        self.assertNotIn(CID, apt)
        self.assertIn("json.query.jq", apt)


if __name__ == "__main__":
    unittest.main()
