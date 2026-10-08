from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import r2_structured_table_direct_adequacy_v1 as table


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical/astra_runtime/tmp"
SOURCE = TMP / "R2_TABLE_DIRECT_SOURCE.json"
XLSX = TMP / "R2_TABLE_DIRECT_OUTPUT.xlsx"
SQLITE = TMP / "R2_TABLE_DIRECT_OUTPUT.sqlite"

XLSX_GOAL = (
    "Create canonical/astra_runtime/tmp/R2_TABLE_DIRECT_OUTPUT.xlsx from "
    "canonical/astra_runtime/tmp/R2_TABLE_DIRECT_SOURCE.json with columns "
    "capability_id, status, source_type, provides, incremental_spend_usd"
)
SQLITE_GOAL = (
    "Create canonical/astra_runtime/tmp/R2_TABLE_DIRECT_OUTPUT.sqlite from "
    "canonical/astra_runtime/tmp/R2_TABLE_DIRECT_SOURCE.json with table named "
    "verified_capabilities, status VERIFIED_BOUND_CAPABILITY, and columns "
    "capability_id, status, source_type, provides, incremental_spend_usd"
)


class R2StructuredTableDirectAdequacyV1Tests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True, exist_ok=True)
        SOURCE.write_text(json.dumps({
            "capabilities": {
                "cap.a": {
                    "status": "VERIFIED_BOUND_CAPABILITY",
                    "source_type": "apt",
                    "provides": ["x"],
                    "incremental_spend_usd": 0,
                },
                "cap.b": {
                    "status": "VERIFIED_BOUND_CAPABILITY",
                    "source_type": "python_stdlib",
                    "provides": ["y"],
                    "incremental_spend_usd": 0,
                },
            }
        }), encoding="utf-8")
        for path in (XLSX, SQLITE):
            if path.exists():
                path.unlink()

    def tearDown(self):
        for path in (SOURCE, XLSX, SQLITE):
            if path.exists():
                path.unlink()

    def test_real_registry_preflight_selects_xlsx_verified_producer(self):
        out = table.preflight({"task_id": "xlsx", "goal": XLSX_GOAL})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["status"], "DIRECT_STRUCTURED_TABLE_ADEQUACY_ROUTE_MATCHED")
        self.assertEqual(out["format"], "xlsx")
        self.assertEqual(out["capability_id"], "xlsx.table.create_from_json_records")
        self.assertEqual(out["verifier_capability_id"], "xlsx.table.verify_against_json_records")
        self.assertFalse(out["preflight_execution_authority"])

    def test_real_registry_preflight_selects_sqlite_verified_producer(self):
        out = table.preflight({"task_id": "sqlite", "goal": SQLITE_GOAL})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["format"], "sqlite")
        self.assertEqual(out["capability_id"], "sqlite.table.create_from_json_records")
        self.assertEqual(out["verifier_capability_id"], "sqlite.table.verify_against_json_records")
        self.assertEqual(out["table_name"], "verified_capabilities")
        self.assertEqual(out["status_value"], "VERIFIED_BOUND_CAPABILITY")

    def test_extra_instruction_is_outside_exact_family(self):
        out = table.preflight({
            "task_id": "extra",
            "goal": XLSX_GOAL + ". Then upload it somewhere.",
        })
        self.assertFalse(out["matched"])
        self.assertEqual(out["status"], "NOT_APPLICABLE")

    @patch.object(table.live_bound, "run_raw_goal")
    def test_verified_xlsx_semantics_commit_and_prove_adequacy(self, execute):
        pf = table.preflight({"task_id": "xlsx-pass", "goal": XLSX_GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(request):
            XLSX.write_bytes(b"PK\x03\x04producer-bytes")
            return {
                "pass": True,
                "compiled_capability_id": pf["capability_id"],
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }

        execute.side_effect = fake_execute
        out = table.run(
            {"task_id": "xlsx-pass", "goal": XLSX_GOAL},
            verifier_provider=lambda _: {
                "verified": True,
                "producer_independent_verifier": True,
            },
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_acceptance_complete"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["policy_adequacy_authority"])
        self.assertTrue(out["transaction_committed"])
        self.assertFalse(out["transaction_rolled_back"])
        self.assertEqual(
            len(out["accepted_raw_obligation_ids"]),
            out["raw_acceptance_obligation_count"],
        )

    @patch.object(table.live_bound, "run_raw_goal")
    def test_failed_acceptance_restores_preexisting_sqlite_bytes(self, execute):
        old = b"old-sqlite-bytes"
        SQLITE.write_bytes(old)
        pf = table.preflight({"task_id": "sqlite-restore", "goal": SQLITE_GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(request):
            SQLITE.write_bytes(b"replacement-bad")
            return {
                "pass": True,
                "compiled_capability_id": pf["capability_id"],
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }

        execute.side_effect = fake_execute
        out = table.run(
            {"task_id": "sqlite-restore", "goal": SQLITE_GOAL},
            verifier_provider=lambda _: {
                "verified": False,
                "producer_independent_verifier": True,
            },
        )
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertEqual(SQLITE.read_bytes(), old)
        self.assertFalse(out["policy_adequacy_authority"])

    @patch.object(table.live_bound, "run_raw_goal")
    def test_execution_identity_mismatch_rolls_back_new_file(self, execute):
        pf = table.preflight({"task_id": "xlsx-id", "goal": XLSX_GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(request):
            XLSX.write_bytes(b"PK\x03\x04wrong")
            return {
                "pass": True,
                "compiled_capability_id": "wrong.capability",
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }

        execute.side_effect = fake_execute
        out = table.run({"task_id": "xlsx-id", "goal": XLSX_GOAL})
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertFalse(XLSX.exists())
        self.assertEqual(out["status"], "FAIL_CLOSED")


    @patch.object(table, "_independent_verify")
    @patch.object(table.live_bound, "run_raw_goal")
    def test_source_mutation_fails_closed_and_restores_output(self, execute, verify):
        old = b"old-artifact"
        XLSX.write_bytes(old)
        pf = table.preflight({"task_id": "table-source-mutation", "goal": XLSX_GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(request):
            XLSX.write_bytes(b"replacement")
            SOURCE.write_text('{"mutated":true}', encoding="utf-8")
            return {
                "pass": True,
                "compiled_capability_id": pf["capability_id"],
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }

        execute.side_effect = fake_execute
        out = table.run({"task_id": "table-source-mutation", "goal": XLSX_GOAL})
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(out["transaction_rolled_back"])
        self.assertEqual(XLSX.read_bytes(), old)
        verify.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
