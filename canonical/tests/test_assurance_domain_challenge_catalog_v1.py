from __future__ import annotations

import unittest

from canonical.runtime import assurance_closure_reference_checker_v1 as reference
from canonical.runtime import assurance_domain_challenge_catalog_v1 as catalog


class AssuranceDomainChallengeCatalogV1Tests(unittest.TestCase):
    def test_all_v1_52_to_v1_67_challenges_fit_existing_kernel(self):
        out = catalog.evaluate_all()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["challenge_count"], 16)
        for row in out["rows"]:
            self.assertTrue(row["existing_kernel_expressive"], row)
            self.assertFalse(row["new_primitive_required"], row)
            self.assertEqual(row["status"], "OPEN__ASSURANCE_RESIDUAL")

    def test_independent_reference_agrees_challenges_are_structurally_open(self):
        for challenge_id in sorted(catalog.CHALLENGES):
            graph = catalog.graph_for(challenge_id)
            out = reference.check(graph)
            self.assertEqual(out["status"], "STRUCTURAL_OPEN", (challenge_id, out))
            self.assertTrue(out["representation_closure"], (challenge_id, out))
            self.assertFalse(out["proof_closure"], (challenge_id, out))


if __name__ == "__main__":
    unittest.main()
