from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / "canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def blob(path: Path) -> str:
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


class CurrentResidualOQAdapterReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc=load(CURRENT)
        cls.rows={x["residual_id"]:x for x in cls.doc["classifications"]}

    def test_oq_is_primary_escape_research_compression(self):
        row=self.rows["ESCAPE_OQ_SHARED_ACCEPTANCE_LAWS"]
        self.assertEqual(row["scheduler_role"],"PRIMARY_ESCAPE_ACCEPTANCE_RESEARCH_COMPRESSION")
        self.assertFalse(row["row_specific_labels_are_primary_research_programs"])
        self.assertIn("O_OBJECTIVE_ACCEPTANCE_11",row["current_truth"])
        self.assertIn("Q_QUALITATIVE_RELATIVE_ORDER_2",row["current_truth"])
        self.assertEqual(
            self.doc["next_shared_execution_cut"][0],
            "INSTANTIATE_BOUND_O_SHARED_SCOPE_LIFT_LAW_WITH_REAL_CONTENT_ADDRESSED_SCOPE_COMPLETE_BRAIN_PROOFS_FOR_CURRENT_O11_ROWS__PREFER_ONE_PROOF_COVERING_MULTIPLE_ROWS",
        )
        self.assertEqual(
            self.doc["next_shared_execution_cut"][1],
            "ATTACK_Q2_GDPVAL_AND_AA_BRIEFCASE_WITH_ONE_SHARED_AUTHENTICATED_PROFESSIONAL_QUALITY_ORDER_OR_ROBUST_COMMON_POLICY_DOMINANCE_LAW",
        )

    def test_o_shared_law_is_bound_and_row_instantiation_is_now_primary(self):
        row=self.rows["ESCAPE_OQ_SHARED_ACCEPTANCE_LAWS"]
        self.assertTrue(row["o_shared_law_bound"])
        self.assertEqual(row["o_current_row_acceptance_closed_count"],0)
        self.assertIn("O11_SHARED_SCOPE_LIFT_LAW_BOUND",row["current_truth"])
        self.assertIn("O_ROW_ACCEPTANCE_CLOSED_0_OF_11",row["current_truth"])
        self.assertIn("Q2_SHARED_QUALITY_LAW_OPEN",row["current_truth"])
        self.assertIn("SCOPE_COMPLETE_BRAIN_PROOFS_FOR_CURRENT_O11_ROWS",row["exact_remaining_class"])
        self.assertIn("Q_QUALITY_ORDER",row["exact_remaining_class"])
        self.assertEqual(
            row["o_shared_law_activation"],
            "canonical/governance/ESCAPE_O_OBJECTIVE_ACCEPTANCE_SHARED_LAW_ACTIVATION_20261010_V1.json",
        )
        self.assertEqual(
            row["o_shared_law_verification"],
            "canonical/verification/CURRENT_ESCAPE_O_OBJECTIVE_ACCEPTANCE_VERIFY_20261010_V1.json",
        )

    def test_gap_a_adapter_construction_is_closed_but_rows_remain_open(self):
        row=self.rows["ESCAPE_GAP_A_ACQUISITION_TOTALITY"]
        self.assertEqual(
            row["existing_binding"],
            "canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V6.json",
        )
        self.assertEqual(row["gap_a_policy_cover_adapter"]["real_row_proofs"],0)
        self.assertIn("ADAPTER_CONSTRUCTION_CLOSED",row["current_gate_status"])
        self.assertIn("REAL_ROW_PROOFS_0_OF_10",row["exact_remaining_class"])

    def test_gap_b_reuses_v6_binding(self):
        self.assertEqual(
            self.rows["ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS"]["existing_binding"],
            "canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V6.json",
        )

    def test_new_exact_sources_are_content_bound(self):
        expected={
            "canonical/governance/CURRENT_ESCAPE_OQ_FRONTIER_REDUCTION_20261010_V1.json":"06ed743742a919615841a77fc9b1cc4e6fadf7f8",
            "canonical/governance/ESCAPE_O_OBJECTIVE_ACCEPTANCE_SHARED_LAW_ACTIVATION_20261010_V1.json":"95278c5850ccba2087b686b7bb9bc2cc7af93b96",
            "canonical/verification/CURRENT_ESCAPE_O_OBJECTIVE_ACCEPTANCE_VERIFY_20261010_V1.json":"a9fec9307a193a43c6f478b4a21b2e26e335fcd4",
            "canonical/runtime/current_escape_o_objective_acceptance_v1.py":"a329ce2d14dd6f23d06f981c090b535bfd43fb52",
            "canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V6.json":"a6fe5eda7b596d5a24cf75bc9b046bf53f4fe7be",
            "canonical/governance/ESCAPE_GAP_A_POLICY_COVER_ADAPTER_ACTIVATION_20261010_V1.json":"7eaa5c0a403cfd9e6d131cecdc7cb9a243843872",
            "canonical/verification/ESCAPE_GAP_A_POLICY_COVER_ADAPTER_VERIFY_20261010_V1.json":"4c1ad0d785d4a4d354c01a4d09e412d294304195",
            "canonical/verification/ESCAPE_GAP_A_POLICY_COVER_ADAPTER_ACTIVATION_VERIFY_20261010_V1.json":"fbd067e5aa8cf6648f61395fcba39d1f413f9bd1",
        }
        by_path={x["path"]:x for x in self.doc["sources"]}
        for path,sha in expected.items():
            self.assertEqual(by_path[path]["git_blob_sha"],sha)
            self.assertEqual(blob(ROOT/path),sha)

    def test_zero_credit_and_reuse_first_are_preserved(self):
        self.assertEqual(self.doc["accounting"]["capability_credit_delta"],0)
        self.assertEqual(self.doc["accounting"]["acceptance_credit_delta"],0)
        self.assertEqual(self.doc["accounting"]["ownership_credit_delta"],0)
        self.assertEqual(self.doc["accounting"]["terminal_credit_delta"],0)
        self.assertIn("REUSE_FIRST_POLICY",self.doc["global_rule"])
        self.assertIn("GAP_A_ADAPTER_IS_REALIZATION_BRIDGE_NOT_O_Q_CLOSURE",self.doc["hard_nonclaims"])
        self.assertIn("REAL_GAP_A_ROW_PROOFS_REMAIN_ZERO_OF_TEN",self.doc["hard_nonclaims"])


if __name__=="__main__":
    unittest.main(verbosity=2)
