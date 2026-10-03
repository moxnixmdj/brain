from __future__ import annotations
import copy,unittest
from canonical.runtime.synthesis_scope_relation_verifier_v1 import evaluate,load,CERT

class TestSynthesisScopeRelationV1(unittest.TestCase):
    def setUp(self):
        self.c=load(CERT)

    def test_current_candidate_passes(self):
        out=evaluate(self.c)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["scope_relation_verified"])
        self.assertEqual(out["scope_relation"],"PROVEN_STRONGER")
        self.assertEqual(out["acceptance_credit_delta"],0)

    def test_wrong_relation_fails(self):
        c=copy.deepcopy(self.c); c["claimed_relation"]="EXACT"
        self.assertFalse(evaluate(c)["pass"])

    def test_performance_credit_overclaim_fails(self):
        c=copy.deepcopy(self.c); c["performance_credit_requested"]=True
        self.assertFalse(evaluate(c)["pass"])

    def test_missing_nonclaim_fails(self):
        c=copy.deepcopy(self.c); c["deliberately_unproved"].remove("matched_quality_noninferiority")
        self.assertFalse(evaluate(c)["pass"])

    def test_dimension_mapping_mutation_fails(self):
        c=copy.deepcopy(self.c)
        c["proof"]["exact_dimension_mappings"][0]["required_literals"][0]="not present in source"
        self.assertFalse(evaluate(c)["pass"])

if __name__=="__main__":
    unittest.main()
