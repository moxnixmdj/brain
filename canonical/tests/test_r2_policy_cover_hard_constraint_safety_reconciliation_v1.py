from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
R2=ROOT/"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
REC=ROOT/"canonical/governance/R2_POLICY_COVER_HARD_CONSTRAINT_SAFETY_RECONCILIATION_20261010_V1.json"
THEOREM=ROOT/"canonical/governance/OBSERVATIONAL_EQUIVALENCE_POLICY_COVER_TOTALITY_THEOREM_20261007_V1.json"
GATE=ROOT/"canonical/runtime/observable_policy_cover_totality_gate_v1.py"
EXECUTOR=ROOT/"canonical/runtime/observable_policy_cover_executor_v1.py"
CONTROLLER=ROOT/"canonical/runtime/general_adequate_decision_controller_v1.py"
VERIFY=ROOT/"canonical/verification/R2_POLICY_COVER_SAFETY_REPAIR_INDEPENDENT_REPLAY_VERIFY_20261010_V1.json"

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def blob(path):
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r2=load(R2)
        cls.rec=load(REC)
        cls.verify=load(VERIFY)

    def test_frontier_and_counts_do_not_change(self):
        self.assertIn("__V77__",self.r2["status"])
        self.assertIn("ONE_PRIMARY_FINANCE_SEMANTIC_RESIDUAL_REMAINS",self.r2["status"])
        self.assertFalse(self.r2["general_mechanism_missing"])
        delta=self.rec["semantic_delta"]
        self.assertEqual(delta["direct_route_count_delta"],0)
        self.assertEqual(delta["bounded_family_count_delta"],0)
        self.assertEqual(delta["primary_internal_unsolved_count_delta"],0)
        self.assertFalse(delta["finance_semantic_tail_closed"])
        self.assertFalse(delta["global_open_world_closure_claimed"])
        self.assertEqual(delta["terminal_credit_delta"],0)

    def test_live_information_policy_requires_safe_policy_cover(self):
        pol=self.r2["fixed_point_information_policy"]
        self.assertTrue(pol["policy_cover_positive_regions_require_region_wide_policy_safety"])
        self.assertTrue(pol["policy_cover_positive_regions_require_hard_constraint_scope_complete"])
        self.assertTrue(pol["policy_cover_executor_requires_policy_safety_coverage_proved"])
        self.assertTrue(pol["r2_policy_cover_pass_requires_selected_policy_safety_authority"])

    def test_reconciliation_binds_exact_merged_runtime_and_verification(self):
        b=self.rec["merged_repair"]
        self.assertEqual(b["merge_commit"],"144c74e7c76fee1364e26d31ebef04e2ed7f3cee")
        self.assertEqual(b["theorem_git_blob_sha"],blob(THEOREM))
        self.assertEqual(b["totality_gate_git_blob_sha"],blob(GATE))
        self.assertEqual(b["executor_git_blob_sha"],blob(EXECUTOR))
        self.assertEqual(b["controller_git_blob_sha"],blob(CONTROLLER))
        self.assertEqual(b["verification_git_blob_sha"],blob(VERIFY))
        live=self.r2["policy_cover_hard_constraint_safety_reconciliation"]
        self.assertEqual(live["reconciliation_git_blob_sha"],blob(REC))
        self.assertEqual(live["verification_git_blob_sha"],blob(VERIFY))

    def test_repair_closes_only_the_theorem_runtime_safety_mismatch(self):
        d=self.rec["defect_closed"]
        self.assertFalse(d["adequate_but_unsafe_policy_can_pass"])
        self.assertFalse(d["incomplete_hard_constraint_scope_can_pass"])
        self.assertTrue(d["positive_policy_region_requires_policy_safe_on_every_listed_world"])
        self.assertTrue(d["positive_policy_region_requires_hard_constraint_scope_complete"])
        self.assertTrue(d["executor_requires_policy_safety_coverage_proved"])
        self.assertTrue(d["r2_controller_requires_selected_policy_safety_verified"])

    def test_independent_replay_is_exact_and_zero_credit(self):
        self.assertTrue(self.rec["verification"]["independent_exact_byte_replay"])
        self.assertEqual(self.rec["verification"]["total_tests_passed"],32)
        self.assertEqual(self.rec["verification"]["total_tests_failed"],0)
        self.assertTrue(self.rec["verification"]["py_compile_passed"])
        self.assertEqual(self.verify["accounting"]["terminal_credit_delta"],0)
        self.assertEqual(self.rec["accounting"]["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
