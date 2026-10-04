from __future__ import annotations
import copy, unittest
from canonical.runtime.synthesis_required_claim_coverage_ceiling_lift_verifier_v2 import docs, evaluate

class SynthesisCoverageCeilingV2Tests(unittest.TestCase):
    def test_live_candidate_passes(self):
        out=evaluate(*docs())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["brain_minus_comparator_lower_bound"],0.0)
        self.assertEqual(set(out["remaining_unproved"]),{"metric:matched_quality","matched_quality_noninferiority"})

    def test_missing_superset_relation_fails(self):
        d=list(docs()); d[0]=copy.deepcopy(d[0])
        d[0]["proof_composition"]["verified_source_to_target_relation"]=None
        out=evaluate(*d)
        self.assertFalse(out["pass"])
        self.assertIn("CANDIDATE_RELATION_NOT_SUPERSET",out["errors"])

    def test_historical_extra_failure_fails(self):
        d=list(docs()); d[2]=copy.deepcopy(d[2])
        d[2]["failure"].append("UNRELATED_PREMISE_FAILURE")
        out=evaluate(*d)
        self.assertFalse(out["pass"])
        self.assertIn("HISTORICAL_FAILURE_SET_NOT_SCOPE_ONLY",out["errors"])

    def test_scope_certificate_relation_mutation_fails(self):
        d=list(docs()); d[4]=copy.deepcopy(d[4])
        d[4]["scope_relation"]="INCOMPARABLE"
        out=evaluate(*d)
        self.assertFalse(out["pass"])
        self.assertIn("SCOPE_CERT_NOT_PROVEN_STRONGER",out["errors"])

    def test_semantics_transport_mutation_fails(self):
        d=list(docs()); d[3]=copy.deepcopy(d[3])
        d[3]["verified"]["v1_to_v3_target_semantics_identical"]=False
        out=evaluate(*d)
        self.assertFalse(out["pass"])
        self.assertIn("CURRENT_TARGET_SEMANTICS_NOT_IDENTICAL",out["errors"])

    def test_matched_quality_overclaim_fails(self):
        d=list(docs()); d[0]=copy.deepcopy(d[0])
        d[0]["explicitly_not_proved"]=[]
        out=evaluate(*d)
        self.assertFalse(out["pass"])
        self.assertIn("MATCHED_QUALITY_OVERCLAIM",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
