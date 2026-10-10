import unittest
from canonical.runtime import professional_semantic_v10_totality_basis_v1 as v

class Tests(unittest.TestCase):
 def test_derives_12_exact_totality_candidates(self):
  o=v.verify();self.assertTrue(o["pass"],o);self.assertEqual(o["candidate_count"],12)
  self.assertEqual(len({r["semantic_claim_id"] for r in o["rows"]}),12)
  for r in o["rows"]:
   self.assertTrue(r["claim_scoped_totality_proved"])
   self.assertTrue(r["cc_r1_reality_containment_proved"])
   self.assertTrue(r["cc_r2_mission_soundness_proved"])
   self.assertTrue(r["cc_r3_terminal_closure_proved"])
   self.assertTrue(r["r4_proof_realization_authority"])
 def test_candidate_cannot_self_certify(self):
  o=v.verify();self.assertFalse(o["independent_verified"])
  self.assertFalse(o["positive_route_nonvacuity_proved"])
  self.assertFalse(o["semantic_property_truth_authority"])
  self.assertFalse(o["terminal_authority"])

if __name__=="__main__":unittest.main(verbosity=2)
