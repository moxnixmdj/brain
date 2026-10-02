from __future__ import annotations

import copy
import unittest

from canonical.runtime.p1_composite_scope_repair_verifier_v1 import load_live, evaluate


class P1CompositeScopeRepairTests(unittest.TestCase):
    def test_live_composite_partition_repairs_declared_p1_scope_without_replay(self):
        out=evaluate(**load_live())
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["scope_repair_proved"])
        self.assertEqual(out["required_check_count"],8)
        self.assertEqual(out["required_mutation_count"],9)
        self.assertEqual(out["v4_case_count"],168)
        self.assertEqual(out["terminal_case_count"],60)
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["terminal_results_replayed"],0)
        self.assertFalse(out["promotion_authority"])

    def test_missing_v4_predeclaration_fails_closed(self):
        x=load_live()
        x["binding"]=copy.deepcopy(x["binding"])
        x["binding"]["dependencies"]=[
            p for p in x["binding"]["dependencies"]
            if p!="canonical/runtime/trajectory_failure_typed_ir_proof_v4.py"
        ]
        out=evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("V4_NOT_PREDECLARED_IN_FROZEN_BINDING",out["errors"])

    def test_check_partition_omission_fails_closed(self):
        x=load_live()
        x["reconciliation"]=copy.deepcopy(x["reconciliation"])
        x["reconciliation"]["proof_roles"]["V4_TYPED_CROSS_DOMAIN_PREFLIGHT"].pop()
        out=evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("REQUIRED_CHECK_PARTITION_MISMATCH",out["errors"])

    def test_mutation_overlap_fails_closed(self):
        x=load_live()
        x["reconciliation"]=copy.deepcopy(x["reconciliation"])
        x["reconciliation"]["mutation_roles"]["V4_TYPED_CROSS_DOMAIN_PREFLIGHT"].append(
            "SELECT_DOWNSTREAM_SYMPTOM"
        )
        out=evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("REQUIRED_MUTATION_PARTITION_NOT_DISJOINT",out["errors"])

    def test_terminal_receipt_failure_fails_closed(self):
        x=load_live()
        x["terminal"]=copy.deepcopy(x["terminal"])
        rows=x["terminal"]["reduction_input"]["wave"]["parent_portfolio_receipts"]["T0"]
        row=next(r for r in rows if r.get("behavior_id")=="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001")
        row["direct_instrumentation_pass"]=False
        out=evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("TERMINAL_RECEIPT_NOT_PASS:T0",out["errors"])

    def test_v4_independent_verification_required(self):
        x=load_live()
        x["v4_verification"]=copy.deepcopy(x["v4_verification"])
        x["v4_verification"]["status"]="FAIL"
        out=evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("V4_INDEPENDENT_VERIFICATION_NOT_PASS",out["errors"])

    def test_no_acceptance_or_family_credit_is_created(self):
        out=evaluate(**load_live())
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
