import unittest
from pathlib import Path
from canonical.runtime import professional_r12_safe_certification_disposition_claim_verify_v1 as v

class Tests(unittest.TestCase):
    def test_current_exact_bytes_pass(self):
        o=v.verify()
        self.assertTrue(o["pass"],o)
        self.assertTrue(o["safe_property_truth_proved"])
        self.assertFalse(o["stronger_r12_semantic_sufficiency_proved"])
        self.assertFalse(o["whole_leaf_scope_equivalence_proved"])
        self.assertEqual(o["positive_control_valuations_verified"],16)
    def test_safe_and_stronger_claim_ids_are_distinct(self):
        self.assertNotEqual(v.CLAIM_ID,v.STRONGER_CLAIM_ID)
    def test_verifier_never_grants_terminal_credit(self):
        o=v.verify()
        self.assertFalse(o["terminal_authority"])
        self.assertEqual(o["terminal_credit_delta"],0)

if __name__=="__main__":unittest.main(verbosity=2)
