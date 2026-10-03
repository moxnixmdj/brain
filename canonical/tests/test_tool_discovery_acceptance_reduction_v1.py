from __future__ import annotations
import copy
import unittest

from canonical.runtime import tool_discovery_acceptance_reduction_v1 as r

class Tests(unittest.TestCase):
    def test_exact_current_reduction_closes_tool_discovery(self):
        out=r.evaluate()
        self.assertTrue(out["status"].startswith("PASS__"),out)
        self.assertEqual(out["result_family_status"],"PASS")
        self.assertEqual(out["scope_basis"],"EXACT_COMPLETE_TARGET_CASE_UNIVERSE")
        self.assertEqual(out["closure_mode"],"ABSOLUTE_DOMINANCE")
        self.assertEqual(out["witness_reason"],"THEORETICAL_CEILING_DOMINANCE")
        self.assertEqual(out["closed_family_count"],4)
        self.assertEqual(out["open_family_count"],15)
        self.assertEqual(out["newly_closed_families"],["TOOL_DISCOVERY_SELECTION_AND_LEARNING"])
        self.assertEqual(out["terminal_cases_replayed"],0)
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertFalse(out["promotion_authority"])

    def test_scope_receipt_cannot_be_self_or_unverified(self):
        scope=r._load(r.SCOPE)
        scope=copy.deepcopy(scope)
        scope["status"]="CANDIDATE"
        scope["public_runner"]["conclusion"]="failure"
        out=r.evaluate(scope_override=scope)
        self.assertEqual(out["status"],"FAIL_CLOSED__SCOPE_RECEIPT_NOT_ADMISSIBLE")
        self.assertEqual(out["result_family_status"],"DEFINED_RESULT_OPEN")

    def test_scope_basis_must_be_exact_complete_target_universe(self):
        scope=r._load(r.SCOPE)
        scope=copy.deepcopy(scope)
        scope["basis_kind"]="FINITE_SAMPLE"
        out=r.evaluate(scope_override=scope)
        self.assertEqual(out["status"],"FAIL_CLOSED__SCOPE_RECEIPT_NOT_ADMISSIBLE")

    def test_ceiling_witness_mutation_fails_closed(self):
        w=r._load(r.WITNESS)
        w=copy.deepcopy(w)
        w["result"]["brain_lower_bound"]=0.99
        out=r.evaluate(witness_override=w)
        self.assertEqual(out["status"],"FAIL_CLOSED__CEILING_WITNESS_NOT_ADMISSIBLE")

if __name__=="__main__":
    unittest.main(verbosity=2)
