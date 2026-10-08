from __future__ import annotations

from hashlib import sha256
import json
import unittest
from pathlib import Path

from canonical.runtime import r2_tabular_artifact_direct_adequacy_v1 as tabular


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical/astra_runtime/tmp"
SOURCE_REL = "canonical/astra_runtime/tmp/R2_TABULAR_SOURCE.json"
SQLITE_REL = "canonical/astra_runtime/tmp/R2_TABULAR_OUTPUT.sqlite"
XLSX_REL = "canonical/astra_runtime/tmp/R2_TABULAR_OUTPUT.xlsx"

SQLITE_GOAL = (
    f"Read {SOURCE_REL}. Create a SQLite database at {SQLITE_REL} with a table named "
    "verified_records containing exactly one row for every record containing the exact "
    "scalar value VERIFIED_BOUND_CAPABILITY and columns capability_id, status, name. "
    "Finally independently query the SQLite database and verify that exactly those source "
    "records appear once and that every stored value matches the source JSON."
)

XLSX_GOAL = (
    f"Read {SOURCE_REL}. Create an XLSX spreadsheet workbook at {XLSX_REL} containing "
    "exactly one row for every record in the unambiguous source record collection with "
    "columns record_id, status, name. Finally independently reopen the workbook and verify "
    "that every source record appears exactly once and that every stored value matches the "
    "source JSON."
)


class R2TabularArtifactDirectAdequacyV1Tests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True, exist_ok=True)
        self.source = ROOT / SOURCE_REL
        self.sqlite = ROOT / SQLITE_REL
        self.xlsx = ROOT / XLSX_REL
        self.source.write_text(
            json.dumps(
                {
                    "records": {
                        "cap-a": {
                            "status": "VERIFIED_BOUND_CAPABILITY",
                            "name": "alpha",
                        },
                        "cap-b": {
                            "status": "OTHER",
                            "name": "beta",
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        for p in (self.sqlite, self.xlsx):
            if p.exists():
                p.unlink()

    def tearDown(self):
        for p in (self.source, self.sqlite, self.xlsx):
            if p.exists():
                p.unlink()

    def test_sqlite_real_registry_preflight_binds_verified_independent_pair(self):
        out = tabular.preflight({"task_id": "sqlite-preflight", "goal": SQLITE_GOAL})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["status"], "DIRECT_TABULAR_ADEQUACY_ROUTE_MATCHED")
        self.assertEqual(out["kind"], "sqlite")
        self.assertEqual(out["producer_capability_id"], "sqlite.table.create_from_json_records")
        self.assertEqual(
            out["verifier_capability_id"],
            "sqlite.table.verify_against_json_records",
        )
        self.assertEqual(out["table_name"], "verified_records")
        self.assertEqual(out["status_value"], "VERIFIED_BOUND_CAPABILITY")
        self.assertEqual(out["columns"], ["capability_id", "status", "name"])
        self.assertFalse(out["preflight_execution_authority"])

    def test_xlsx_real_registry_preflight_binds_verified_independent_pair(self):
        out = tabular.preflight({"task_id": "xlsx-preflight", "goal": XLSX_GOAL})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["status"], "DIRECT_TABULAR_ADEQUACY_ROUTE_MATCHED")
        self.assertEqual(out["kind"], "xlsx")
        self.assertEqual(out["producer_capability_id"], "xlsx.table.create_from_json_records")
        self.assertEqual(
            out["verifier_capability_id"],
            "xlsx.table.verify_against_json_records",
        )
        self.assertEqual(out["columns"], ["record_id", "status", "name"])
        self.assertFalse(out["preflight_execution_authority"])

    def test_extra_instruction_is_not_in_exact_family(self):
        out = tabular.preflight(
            {
                "task_id": "tabular-extra",
                "goal": SQLITE_GOAL + " Then upload it somewhere.",
            }
        )
        self.assertFalse(out["matched"])
        self.assertEqual(out["status"], "NOT_APPLICABLE")

    def test_sqlite_identity_column_requirement_fails_closed_before_execution(self):
        bad = SQLITE_GOAL.replace(
            "columns capability_id, status, name",
            "columns status, name",
        )
        out = tabular.preflight({"task_id": "sqlite-bad-id", "goal": bad})
        self.assertTrue(out["matched"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("SQLITE_CAPABILITY_ID_COLUMN_REQUIRED", out["reason"])

    def test_sqlite_independent_query_commits_and_proves_adequacy(self):
        payload = b"sqlite-artifact"

        def produce(pf):
            self.sqlite.write_bytes(payload)
            return {
                "output_verified": True,
                "output_path": SQLITE_REL,
                "output_sha256": sha256(payload).hexdigest(),
                "row_count": 1,
                "columns": ["capability_id", "status", "name"],
                "table_name": "verified_records",
                "status_value": "VERIFIED_BOUND_CAPABILITY",
            }

        def verify(pf):
            return {
                "verified": True,
                "producer_independent_verifier": True,
                "sqlite_path": SQLITE_REL,
                "sqlite_sha256": sha256(payload).hexdigest(),
                "verified_rows": 1,
                "columns": ["capability_id", "status", "name"],
                "table_name": "verified_records",
                "status_value": "VERIFIED_BOUND_CAPABILITY",
            }

        out = tabular.run(
            {"task_id": "sqlite-pass", "goal": SQLITE_GOAL},
            producer_provider=produce,
            verifier_provider=verify,
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_acceptance_complete"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["policy_adequacy_authority"])
        self.assertTrue(out["transaction_committed"])
        self.assertTrue(self.sqlite.is_file())
        self.assertEqual(
            len(out["accepted_raw_obligation_ids"]),
            out["raw_acceptance_obligation_count"],
        )

    def test_xlsx_independent_reopen_commits_and_proves_adequacy(self):
        payload = b"PK\x03\x04xlsx-artifact"

        def produce(pf):
            self.xlsx.write_bytes(payload)
            return {
                "output_verified": True,
                "output_path": XLSX_REL,
                "output_sha256": sha256(payload).hexdigest(),
                "row_count": 2,
                "columns": ["record_id", "status", "name"],
            }

        def verify(pf):
            return {
                "verified": True,
                "producer_independent_verifier": True,
                "xlsx_path": XLSX_REL,
                "xlsx_sha256": sha256(payload).hexdigest(),
                "verified_rows": 2,
                "columns": ["record_id", "status", "name"],
            }

        out = tabular.run(
            {"task_id": "xlsx-pass", "goal": XLSX_GOAL},
            producer_provider=produce,
            verifier_provider=verify,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["kind"], "xlsx")
        self.assertTrue(out["policy_adequacy_authority"])
        self.assertTrue(out["transaction_committed"])
        self.assertTrue(self.xlsx.is_file())

    def test_failed_independent_acceptance_restores_preexisting_bytes(self):
        old = b"old-good-bytes"
        replacement = b"bad-replacement"
        self.sqlite.write_bytes(old)

        def produce(pf):
            self.sqlite.write_bytes(replacement)
            return {
                "output_verified": True,
                "output_path": SQLITE_REL,
                "output_sha256": sha256(replacement).hexdigest(),
                "row_count": 1,
                "columns": ["capability_id", "status", "name"],
                "table_name": "verified_records",
                "status_value": "VERIFIED_BOUND_CAPABILITY",
            }

        out = tabular.run(
            {"task_id": "sqlite-restore", "goal": SQLITE_GOAL},
            producer_provider=produce,
            verifier_provider=lambda pf: {"verified": False},
        )
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertEqual(self.sqlite.read_bytes(), old)
        self.assertFalse(out["policy_adequacy_authority"])

    def test_hash_binding_mismatch_rolls_back_new_xlsx_artifact(self):
        payload = b"PK\x03\x04xlsx-artifact"

        def produce(pf):
            self.xlsx.write_bytes(payload)
            return {
                "output_verified": True,
                "output_path": XLSX_REL,
                "output_sha256": sha256(payload).hexdigest(),
                "row_count": 2,
                "columns": ["record_id", "status", "name"],
            }

        out = tabular.run(
            {"task_id": "xlsx-hash-fail", "goal": XLSX_GOAL},
            producer_provider=produce,
            verifier_provider=lambda pf: {
                "verified": True,
                "producer_independent_verifier": True,
                "xlsx_path": XLSX_REL,
                "xlsx_sha256": "0" * 64,
                "verified_rows": 2,
                "columns": ["record_id", "status", "name"],
            },
        )
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertFalse(self.xlsx.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
