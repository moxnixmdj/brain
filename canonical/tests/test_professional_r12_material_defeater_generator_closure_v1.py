from copy import deepcopy
import unittest
from canonical.runtime import professional_r12_material_defeater_generator_closure_v1 as v

def r12():
    return {
      "property_claim_id":v.PROPERTY_CLAIM_ID,
      "scope_claim_id":v.SCOPE_CLAIM_ID,
      "leaf_id":v.LEAF_ID,
      "derived":{"all_eight_root_contract_clauses_verified":True,"verified_clause_count":8},
      "stronger_target_residual":{"obligation":v.OBLIGATION,"state":"OPEN"},
      "cc_r3_terminal_closure_proved":False,
    }

def cert():
    return {
      "schema":v.CERT_SCHEMA,
      "property_claim_id":v.PROPERTY_CLAIM_ID,
      "scope_claim_id":v.SCOPE_CLAIM_ID,
      "leaf_id":v.LEAF_ID,
      "obligation":v.OBLIGATION,
      "proof_basis":"LOSSLESS_DECOMPOSITION_OR_GENERATOR_CLOSURE",
      "scope_complete":True,
      "generator_or_universal_cover_complete":True,
      "all_material_defeaters_in_scope_covered":True,
      "uncovered_material_defeater_complement_empty":True,
      "decision_null_or_resolved_for_every_covered_defeater":True,
      "independent_verified":True,
      "independent_verifier_id":"independent-verifier",
      "content_addressed":True,
      "fail_closed_on_unknown":True,
      "finite_catalog_only":False,
      "eight_clause_count_only":False,
      "unknown_remainder":[],
    }

class Tests(unittest.TestCase):
    def test_exact_generator_closure_proves_only_cc_r3(self):
        o=v.evaluate(r12(),cert())
        self.assertTrue(o["pass"],o)
        self.assertTrue(o["material_defeater_totality_proved"])
        self.assertTrue(o["cc_r3_terminal_closure_proved"])
        self.assertFalse(o["semantic_property_truth_authority"])
        self.assertFalse(o["r4_proof_realization_authority"])
    def test_finite_catalog_is_rejected(self):
        c=cert();c["finite_catalog_only"]=True
        o=v.evaluate(r12(),c);self.assertFalse(o["pass"])
        self.assertEqual(o["reason"],"FINITE_CATALOG_CANNOT_AUTHORIZE_TOTALITY")
    def test_eight_clause_count_is_rejected(self):
        c=cert();c["eight_clause_count_only"]=True
        o=v.evaluate(r12(),c);self.assertFalse(o["pass"])
        self.assertEqual(o["reason"],"CLAUSE_COUNT_CANNOT_AUTHORIZE_TOTALITY")
    def test_unknown_remainder_is_rejected(self):
        c=cert();c["unknown_remainder"]=["UNMAPPED"]
        o=v.evaluate(r12(),c);self.assertFalse(o["pass"])
        self.assertEqual(o["reason"],"UNKNOWN_REMAINDER_NONEMPTY")
    def test_missing_independent_verification_is_rejected(self):
        c=cert();c["independent_verified"]=False
        o=v.evaluate(r12(),c);self.assertFalse(o["pass"])
        self.assertEqual(o["reason"],"CERT_PREMISE_UNPROVED:independent_verified")
    def test_cross_claim_transport_is_rejected(self):
        c=cert();c["property_claim_id"]="0"*64
        o=v.evaluate(r12(),c);self.assertFalse(o["pass"])
        self.assertEqual(o["reason"],"CERT_BINDING_MISMATCH:property_claim_id")
    def test_unsound_route_is_rejected(self):
        c=cert();c["proof_basis"]="KNOWN_CATALOG"
        o=v.evaluate(r12(),c);self.assertFalse(o["pass"])
        self.assertEqual(o["reason"],"CERT_PROOF_BASIS_NOT_SOUND_ROUTE")

if __name__=="__main__":
    unittest.main(verbosity=2)
