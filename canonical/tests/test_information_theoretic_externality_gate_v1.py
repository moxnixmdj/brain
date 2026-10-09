from __future__ import annotations
import unittest
from canonical.runtime import information_theoretic_externality_gate_v1 as gate


def cert():
    obligation = "O1"
    return {
        "schema": gate.CERT_SCHEMA,
        "target_obligation_id": obligation,
        "scope_complete": True,
        "independent_or_objective": True,
        "missing_information_class": "ONE_POLICY_CHANGING_BIT",
        "indistinguishability_witness": {
            "world_1_id": "w1",
            "world_2_id": "w2",
            "world_1_observation_sha256": "a" * 64,
            "world_2_observation_sha256": "a" * 64,
            "world_1_required_action_sha256": "b" * 64,
            "world_2_required_action_sha256": "c" * 64,
        },
        "internal_route_falsification": [
            {
                "route_class": route,
                "status": "PROVED_UNAVAILABLE_OR_INSUFFICIENT",
                "proof_sha256": f"{i:064x}",
                "target_obligation_id": obligation,
            }
            for i, route in enumerate(sorted(gate.MANDATORY_ROUTE_CLASSES), start=1)
        ],
    }


class InformationTheoreticExternalityGateV1Tests(unittest.TestCase):
    def test_complete_indistinguishability_and_route_exhaustion_passes(self):
        out = gate.verify_certificate(cert())
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["information_theoretic_externality_proved"])

    def test_missing_route_class_fails_closed(self):
        c = cert()
        c["internal_route_falsification"].pop()
        out = gate.verify_certificate(c)
        self.assertFalse(out["pass"])
        self.assertIn("MANDATORY_ROUTE_CLASSES_NOT_EXHAUSTED", out["reason"])

    def test_same_required_action_is_not_externality(self):
        c = cert()
        c["indistinguishability_witness"]["world_2_required_action_sha256"] = "b" * 64
        out = gate.verify_certificate(c)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "WORLDS_DO_NOT_REQUIRE_DIFFERENT_ACTIONS")

    def test_different_observation_is_not_information_theoretic_boundary(self):
        c = cert()
        c["indistinguishability_witness"]["world_2_observation_sha256"] = "d" * 64
        out = gate.verify_certificate(c)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "WORLDS_NOT_OBSERVATIONALLY_INDISTINGUISHABLE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
