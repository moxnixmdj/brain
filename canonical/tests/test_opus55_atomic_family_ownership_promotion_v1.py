from __future__ import annotations
import copy
import unittest

from canonical.runtime.opus55_atomic_family_ownership_promotion_v1 import PATHS, evaluate_documents, load
from canonical.runtime.terminal_projection_consistency_v1 import evaluate_live as evaluate_projection

class AtomicOwnershipPromotionTests(unittest.TestCase):
    def docs(self):
        d={k:load(v) for k,v in PATHS.items()}
        p=evaluate_projection()
        return d,p

    def evaluate(self,d,p):
        return evaluate_documents(d["transaction"],d["matrix"],d["closure"],d["authority"],d["eligibility"],d["tool_package"],d["delegation_package"],p)

    def test_exact_live_candidate_passes(self):
        d,p=self.docs()
        out=self.evaluate(d,p)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["verified_owned_after"],4)
        self.assertFalse(out["terminal_goal_achieved"])

    def test_false_fifth_family_fails_closed(self):
        d,p=self.docs(); d=copy.deepcopy(d)
        d["matrix"]["summary"]["verified_owned_equal_or_better_capabilities"].append("FAKE")
        out=self.evaluate(d,p)
        self.assertFalse(out["pass"])
        self.assertIn("MATRIX_OWNED_SET_MISMATCH",out["errors"])

    def test_missing_independent_eligibility_fails_closed(self):
        d,p=self.docs(); d=copy.deepcopy(d)
        d["eligibility"]["status"]="FAIL"
        out=self.evaluate(d,p)
        self.assertFalse(out["pass"])
        self.assertIn("ELIGIBILITY_NOT_INDEPENDENT_PASS",out["errors"])

    def test_opaque_provider_reintroduction_fails_closed(self):
        d,p=self.docs(); d=copy.deepcopy(d)
        d["tool_package"]["operative_route"]["opaque_target_provider_required"]=True
        out=self.evaluate(d,p)
        self.assertFalse(out["pass"])
        self.assertIn("PACKAGE_ROUTE_MISMATCH:TOOL_DISCOVERY_SELECTION_AND_LEARNING",out["errors"])

    def test_unrelated_acceptance_closure_fails_closed(self):
        d,p=self.docs(); d=copy.deepcopy(d)
        d["transaction"]["to_state"]["acceptance_pending_families"]=14
        out=self.evaluate(d,p)
        self.assertFalse(out["pass"])
        self.assertIn("TRANSACTION_TO_STATE_MISMATCH",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
