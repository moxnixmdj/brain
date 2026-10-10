import unittest
from canonical.runtime import professional_quality_same_subject_composition_gate_v3 as g

class BindingAuthorityCompatibilityTests(unittest.TestCase):
    def test_legacy_absent_global_authority_is_not_self_authority(self):
        self.assertIsNone(g._binding_self_authority_error({"terminal_authority":False}))
    def test_explicit_global_authority_true_fails(self):
        self.assertEqual(
            g._binding_self_authority_error({"global_subject_identity_authority":True,"terminal_authority":False}),
            "GLOBAL_SUBJECT_AUTHORITY_FORBIDDEN",
        )
    def test_terminal_authority_must_remain_explicitly_false(self):
        self.assertEqual(
            g._binding_self_authority_error({}),
            "SUBJECT_BINDING_TERMINAL_AUTHORITY_FORBIDDEN",
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
