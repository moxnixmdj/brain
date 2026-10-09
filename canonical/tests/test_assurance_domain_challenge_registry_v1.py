from __future__ import annotations

import unittest

from canonical.runtime import assurance_closure_compiler_v1 as primary
from canonical.runtime import assurance_closure_reference_checker_v1 as reference
from canonical.runtime import assurance_domain_challenge_registry_v1 as registry


class AssuranceDomainChallengeRegistryV1Tests(unittest.TestCase):
    def test_registry_uses_only_existing_primitives(self):
        out=registry.validate_registry()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["challenge_count"],16)
        self.assertEqual(out["errors"],[])

    def test_every_known_domain_challenge_is_an_ordinary_residual(self):
        out=registry.evaluate_all()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["compiled_count"],16)
        self.assertEqual(out["failed_challenge_ids"],[])
        for row in out["rows"]:
            self.assertTrue(row["representable"],row)
            self.assertTrue(row["ordinary_residual"],row)
            self.assertFalse(row["new_primitive_required"],row)

    def test_primary_and_reference_agree_each_domain_challenge_is_open(self):
        for challenge_id in registry.challenge_ids():
            graph=registry.graph_for(challenge_id)
            p=primary.evaluate(graph)
            r=reference.check(graph)
            self.assertEqual(
                p["closure_gates"]["representation_closure"],
                r["representation_closure"],
                challenge_id,
            )
            self.assertFalse(p["closure_gates"]["proof_closure"],challenge_id)
            self.assertFalse(r["proof_closure"],challenge_id)
            self.assertEqual(p["root_closed"],r["root_closed"],challenge_id)
            self.assertFalse(p["new_primitive_required"],challenge_id)

    def test_origins_cover_v1_52_through_v1_67_without_gap(self):
        observed={
            int(row["origin"].split(".")[1])
            for row in registry.CHALLENGES.values()
        }
        self.assertEqual(observed,set(range(52,68)))


if __name__=="__main__":
    unittest.main()
