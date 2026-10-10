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
            "ATTACK_O11_OBJECTIVE_ACCEPTANCE_WITH_ONE_REUSABLE_SCOPE_COMPLETE_BRAIN_SIDE_ACCEPTANCE_LAW_AND_EXACT_ROW_SCOPE_BINDINGS",
        )
        self.assertEqual(
            self.doc["next_shared_execution_cut"][1],
            "ATTACK_Q2_GDPVAL_AND_AA_BRIEFCASE_WITH_ONE_SHARED_AUTHENTICATED_PROFESSIONAL_QUALITY_ORDER_OR_ROBUST_COMMON_POLICY_DOMINANCE_LAW",
        )

    def test_gap_a_adapter_construction_is_closed_but_rows_remain_open(self):
        row=self.rows["ESCAPE_GAP_A_ACQUISITION_TOTALITY"]
        gap_b=self.rows["ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS"]
        self.assertEqual(row["existing_binding"],gap_b["existing_binding"])
        binding=load(ROOT/row["existing_binding"])
        self.assertEqual(
            binding["predecessor"],
            {
                "path":"canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V6.json",
                "git_blob_sha":"a6fe5eda7b596d5a24cf75bc9b046bf53f4fe7be",
                "inheritance":"ALL_MAIN_V6_GAP_A_POLICY_COVER_ADAPTER_SEMANTICS_PRESERVED",
            },
        )
        self.assertEqual(row["gap_a_policy_cover_adapter"]["real_row_proofs"],0)
        self.assertIn("GAP_A_POLICY_COVER_ADAPTER",row["current_gate_status"])
        self.assertIn("REAL_ROW_PROOFS_0_OF_10",row["exact_remaining_class"])
        self.assertEqual(binding["gap_a_policy_cover_adapter"]["real_gap_a_row_proofs"],0)

    def test_gap_b_reuses_same_current_successor_binding(self):
        self.assertEqual(
            self.rows["ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS"]["existing_binding"],
            self.rows["ESCAPE_GAP_A_ACQUISITION_TOTALITY"]["existing_binding"],
        )

    def test_current_successor_binding_is_dynamic_and_preserves_v6_adapter(self):
        row=self.rows["ESCAPE_GAP_A_ACQUISITION_TOTALITY"]
        binding=load(ROOT/row["existing_binding"])
        audit=binding["successor_executable_audit"]
        self.assertEqual(audit["git_blob_sha"],"e556880aa216673e0e316e11fc6f4ab25d644ce6")
        self.assertEqual(audit["tests"]["git_blob_sha"],"f89cfebb6ffd5d2ff09ac37ba6f2b38e7aa718ed")
        self.assertIn("GAP_A_AND_GAP_B",audit["current_binding_rule"])
        self.assertEqual(
            binding["gap_a_policy_cover_adapter"]["runtime_git_blob_sha"],
            "19b0bdf00eb9b8d76cbf7f1a615e1ce6e89ffbf8",
        )

    def test_new_exact_sources_are_content_bound(self):
        expected={
            "canonical/governance/CURRENT_ESCAPE_OQ_FRONTIER_REDUCTION_20261010_V1.json":"e355f3c168429c96ff0dfa142428ada6c97c47e9",
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
