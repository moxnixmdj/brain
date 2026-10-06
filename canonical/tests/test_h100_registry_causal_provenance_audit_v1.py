import unittest
from canonical.runtime import h100_registry_causal_provenance_audit_v1 as a

class T(unittest.TestCase):
    def test_eight_states(self):
        self.assertEqual(len(a.possible_persistent_states()),8)
    def test_three_bits_capacity(self):
        self.assertEqual(a.causal_capacity_bits(),3)
    def test_counterfactual_changes_behavior(self):
        self.assertTrue(a.behaviorally_distinct((1,1,1),(0,0,0)))
    def test_zero_claim_fails(self):
        self.assertFalse(a.audit_observed_all_pass()["zero_causal_learned_bits_claim_survives"])

if __name__=="__main__": unittest.main(verbosity=2)
