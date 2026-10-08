from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct
from canonical.runtime import r2_tabular_artifact_direct_adequacy_v1 as tabular


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical/astra_runtime/tmp"
SRC_REL = "canonical/astra_runtime/tmp/R2_TABULAR_SOURCE.json"
XLSX_REL = "canonical/astra_runtime/tmp/R2_TABULAR_OUTPUT.xlsx"
SQLITE_REL = "canonical/astra_runtime/tmp/R2_TABULAR_OUTPUT.sqlite"

XLSX_GOAL = (
    f"Create {XLSX_REL} from {SRC_REL} with columns "
    "capability_id, status, name."
)
SQLITE_GOAL = (
    f"Create {SQLITE_REL} from {SRC_REL} for status VERIFIED_BOUND_CAPABILITY "
    "in table named verified_capabilities with columns capability_id, status, name."
)


class R2TabularArtifactDirectAdequacyV1Tests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True, exist_ok=True)
        self.src = ROOT / SRC_REL
        self.xlsx = ROOT / XLSX_REL
        self.sqlite = ROOT / SQLITE_REL
        self.src.write_text(
            json.dumps(
                {
                    "capabilities": {
                        "alpha": {
                            "status": "VERIFIED_BOUND_CAPABILITY",
                            "name": "Alpha",
                        },
                        "beta": {
                            "status": "VERIFIED_BOUND_CAPABILITY",
                            "name": "Beta",
                        },
                    }
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        for p in (self.xlsx, self.sqlite):
            if p.exists():
                p.unlink()

    def tearDown(self):
        for p in (self.src, self.xlsx, self.sqlite):
            if p.exists():
                p.unlink()

    def test_real_registry_preflight_admits_xlsx_family_member(self):
        out = tabular.preflight({"task_id": "xlsx-preflight", "goal": XLSX_GOAL})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["status"], "DIRECT_TABULAR_ADEQUACY_ROUTE_MATCHED")
        self.assertEqual(out["artifact_kind"], "xlsx")
        self.assertEqual(out["capability_id"], "xlsx.table.create_from_json_records")
        self.assertEqual(out["verifier_capability_id"], "xlsx.table.verify_against_json_records")
        self.assertTrue(out["policy_id"].startswith("BOUND_CAPABILITY_POLICY::"))
        self.assertFalse(out["preflight_execution_authority"])

    def test_real_registry_preflight_admits_sqlite_family_member(self):
        out = tabular.preflight({"task_id": "sqlite-preflight", "goal": SQLITE_GOAL})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["status"], "DIRECT_TABULAR_ADEQUACY_ROUTE_MATCHED")
        self.assertEqual(out["artifact_kind"], "sqlite")
        self.assertEqual(out["capability_id"], "sqlite.table.create_from_json_records")
        self.assertEqual(out["verifier_capability_id"], "sqlite.table.verify_against_json_records")

    def test_extra_instruction_is_outside_exact_family(self):
        out = tabular.preflight(
            {
                "task_id": "extra",
                "goal": XLSX_GOAL + " Then upload it somewhere.",
            }
        )
        self.assertFalse(out["matched"])
        self.assertEqual(out["status"], "NOT_APPLICABLE")

    def test_sqlite_family_requires_stable_capability_id_key(self):
        goal = (
            f"Create {SQLITE_REL} from {SRC_REL} for status VERIFIED_BOUND_CAPABILITY "
            "in table named verified_capabilities with columns name, status."
        )
        out = tabular.preflight({"task_id": "bad-id", "goal": goal})
        self.assertTrue(out["matched"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("SQLITE_FIRST_COLUMN_CAPABILITY_ID_REQUIRED", out["reason"])

    @patch.object(tabular, "_verify")
    @patch.object(tabular.live_bound, "run_raw_goal")
    def test_verified_independent_readback_commits_and_proves_adequacy(
        self, execute, verify
    ):
        pf = tabular.preflight({"task_id": "xlsx-pass", "goal": XLSX_GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(request):
            self.xlsx.write_bytes(b"PK\x03\x04producer")
            return {
                "pass": True,
                "compiled_capability_id": pf["capability_id"],
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }

        execute.side_effect = fake_execute
        verify.return_value = {
            "verified": True,
            "producer_independent_verifier": True,
            "verified_rows": 2,
            "columns": ["capability_id", "status", "name"],
        }
        out = tabular.run({"task_id": "xlsx-pass", "goal": XLSX_GOAL})
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_acceptance_complete"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["policy_adequacy_authority"])
        self.assertTrue(out["transaction_committed"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(
            len(out["accepted_raw_obligation_ids"]),
            out["raw_acceptance_obligation_count"],
        )

    @patch.object(tabular, "_verify")
    @patch.object(tabular.live_bound, "run_raw_goal")
    def test_failed_independent_acceptance_rolls_back_new_artifact(
        self, execute, verify
    ):
        pf = tabular.preflight({"task_id": "xlsx-fail", "goal": XLSX_GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(request):
            self.xlsx.write_bytes(b"bad")
            return {
                "pass": True,
                "compiled_capability_id": pf["capability_id"],
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }

        execute.side_effect = fake_execute
        verify.return_value = {"verified": False}
        out = tabular.run({"task_id": "xlsx-fail", "goal": XLSX_GOAL})
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertFalse(self.xlsx.exists())
        self.assertFalse(out["policy_adequacy_authority"])

    @patch.object(tabular, "_verify")
    @patch.object(tabular.live_bound, "run_raw_goal")
    def test_source_mutation_fails_closed_and_rolls_back_output(self, execute, verify):
        old = b"old-artifact"
        self.xlsx.write_bytes(old)
        pf = tabular.preflight({"task_id": "source-mutation", "goal": XLSX_GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(request):
            self.xlsx.write_bytes(b"replacement")
            self.src.write_text('{"mutated":true}', encoding="utf-8")
            return {
                "pass": True,
                "compiled_capability_id": pf["capability_id"],
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }

        execute.side_effect = fake_execute
        out = tabular.run({"task_id": "source-mutation", "goal": XLSX_GOAL})
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(out["transaction_rolled_back"])
        self.assertEqual(self.xlsx.read_bytes(), old)
        verify.assert_not_called()


class R2TabularDirectIntegrationTests(unittest.TestCase):
    @patch.object(direct.tabular_adequacy, "preflight")
    def test_tabular_family_is_reachable_from_direct_preflight(self, preflight):
        preflight.return_value = {
            "matched": True,
            "status": "DIRECT_TABULAR_ADEQUACY_ROUTE_MATCHED",
            "capability_id": "xlsx.table.create_from_json_records",
            "policy_id": "BOUND_CAPABILITY_POLICY::xlsx::goal",
            "goal_sha256": "a" * 64,
            "artifact_kind": "xlsx",
            "json_path": "canonical/source.json",
            "output_path": "canonical/out.xlsx",
        }
        out = direct.preflight({"task_id": "tabular", "goal": "not another direct grammar"})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["route_id"], direct.TABULAR_ARTIFACT_ROUTE_ID)
        self.assertEqual(out["artifact_kind"], "xlsx")
        self.assertFalse(out["preflight_execution_authority"])

    @patch.object(direct.tabular_adequacy, "run")
    @patch.object(direct.tabular_adequacy, "preflight")
    def test_tabular_verified_acceptance_becomes_direct_adequacy(
        self, preflight, run
    ):
        preflight.return_value = {
            "matched": True,
            "status": "DIRECT_TABULAR_ADEQUACY_ROUTE_MATCHED",
            "capability_id": "xlsx.table.create_from_json_records",
            "policy_id": "BOUND_CAPABILITY_POLICY::xlsx::goal",
            "goal_sha256": "b" * 64,
            "artifact_kind": "xlsx",
            "json_path": "canonical/source.json",
            "output_path": "canonical/out.xlsx",
        }
        run.return_value = {
            "pass": True,
            "status": "PASS__TRANSACTIONAL_TABULAR_POLICY_ADEQUACY_VERIFIED",
            "capability_id": "xlsx.table.create_from_json_records",
            "policy_id": "BOUND_CAPABILITY_POLICY::xlsx::goal",
            "goal_sha256": "b" * 64,
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "accepted_raw_obligation_ids": ["RAWREQ:x"],
            "raw_acceptance_obligation_count": 1,
            "raw_result": {"pass": True},
            "authority_boundary": "bounded tabular family",
        }
        out = direct.run({"task_id": "tabular", "goal": "not another direct grammar"})
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["direct_adequacy_authority"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertEqual(
            out["selected_policy_id"],
            "BOUND_CAPABILITY_POLICY::xlsx::goal",
        )

    @patch.object(direct.tabular_adequacy, "run")
    @patch.object(direct.tabular_adequacy, "preflight")
    def test_tabular_acceptance_failure_never_falls_through(
        self, preflight, run
    ):
        preflight.return_value = {
            "matched": True,
            "status": "DIRECT_TABULAR_ADEQUACY_ROUTE_MATCHED",
            "capability_id": "xlsx.table.create_from_json_records",
            "policy_id": "BOUND_CAPABILITY_POLICY::xlsx::goal",
            "goal_sha256": "c" * 64,
            "artifact_kind": "xlsx",
            "json_path": "canonical/source.json",
            "output_path": "canonical/out.xlsx",
        }
        run.return_value = {
            "pass": False,
            "status": "OPEN__INDEPENDENT_TABULAR_ACCEPTANCE_DID_NOT_VERIFY",
            "transaction_rolled_back": True,
        }
        with patch.object(direct.codec_adequacy, "run") as codec_run, \
             patch.object(direct.live_bound, "run_raw_goal") as legacy:
            out = direct.run({"task_id": "tabular", "goal": "not another direct grammar"})
        self.assertFalse(out["pass"])
        self.assertFalse(out["retry_by_other_route_authorized"])
        codec_run.assert_not_called()
        legacy.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
