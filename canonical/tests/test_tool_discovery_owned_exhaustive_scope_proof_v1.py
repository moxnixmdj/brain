from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_owned_exhaustive_scope_proof_v1 as proof


class Tests(unittest.TestCase):
    def test_exact_sources_compile_fail_closed_scope_proof_candidate(self):
        out = proof.evaluate()
        self.assertTrue(out["status"].startswith("PASS__"), out)
        self.assertEqual(out["source_blob_drift"], [])
        self.assertTrue(all(out["semantic_preconditions"].values()), out)
        self.assertTrue(out["v3_global_optimality_counterexample_reproduced"], out)
        self.assertEqual(out["replacement_first_action"]["action"], "DISCOVER")
        self.assertTrue(out["owned_identity_scope"]["every_invocable_discoverable"], out)
        self.assertTrue(all(out["structural_preconditions"].values()), out)
        self.assertTrue(out["universal_scope_proof_candidate"], out)
        self.assertEqual(out["terminal_results_replayed"], 0)
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
