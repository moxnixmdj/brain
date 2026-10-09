from __future__ import annotations

import unittest

from canonical.runtime import information_theoretic_externality_gate_v1 as gate


class InformationTheoreticExternalityGateV1Tests(unittest.TestCase):
    def test_no_certificate_never_becomes_external(self):
        out = gate.verify_certificate(None, pending=[{"work_id": "w1"}])
        self.assertFalse(out["pass"])
        self.assertFalse(out["irreducible_external_information_proved"])
        self.assertEqual(out["reason"], "PROOF_CARRYING_EXTERNALITY_CERTIFICATE_REQUIRED")


    def test_same_observation_but_same_action_is_not_external(self):
        cert = {
            "schema": gate.CERTIFICATE_SCHEMA,
            "status": "PROVED_INFORMATION_THEORETICALLY_EXTERNAL",
            "obligation_ids": ["w1"],
            "exact_missing_information_sha256": "2" * 64,
            "world_pair": {
                "world_1": {
                    "world_id": "W1",
                    "accessible_observation_sha256": "1" * 64,
                    "required_action_sha256": "3" * 64,
                },
                "world_2": {
                    "world_id": "W2",
                    "accessible_observation_sha256": "1" * 64,
                    "required_action_sha256": "3" * 64,
                },
            },
        }
        out = gate.verify_certificate(cert, pending=[{"work_id": "w1"}])
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "WORLD_PAIR_DOES_NOT_REQUIRE_DIFFERENT_ACTIONS",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
