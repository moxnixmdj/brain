import unittest
from canonical.runtime import tool_discovery_frozen_scope_universal_theorem_v1 as th

class Tests(unittest.TestCase):
    def test_theorem(self):
        out = th.evaluate()
        self.assertEqual(out["source_blob_drift"], [], out)
        self.assertTrue(all(out["semantic_preconditions"].values()), out)
        self.assertTrue(all(out["policy_shape_preconditions"].values()), out)
        self.assertIs(out["minimum_missing_scope_semantics_fact_discharged_for_frozen_protocol"], True)
        self.assertIs(out["finite_180_case_transport_used"], False)
        self.assertIs(out["open_domain_identity_exhaustion_claimed"], False)
        self.assertIs(out["dynamic_v3_promoted"], False)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
