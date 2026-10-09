from __future__ import annotations
import sys
import types
import unittest
from unittest.mock import patch

fake_v1 = types.ModuleType("canonical.runtime.one_shot_verified_closure_v1")
fake_v1.run = lambda **kwargs: {}
sys.modules["canonical.runtime.one_shot_verified_closure_v1"] = fake_v1

from canonical.runtime import information_theoretic_externality_gate_v1 as gate
from canonical.runtime import one_shot_reality_closure_v3 as v3


def closure(*, status="OPEN", passed=False, internal=(), evidence=(), weak_external=False):
    return {
        "schema": "PROJECT_BRAIN_ONE_SHOT_VERIFIED_CLOSURE_V1",
        "status": status,
        "pass": passed,
        "fixed_point": True,
        "closure_class": "x",
        "initial_frontier_digest": "i",
        "final_frontier_digest": "f",
        "final_state_sha256": "a" * 64,
        "irreducible_external_information_proved": weak_external,
        "residual": {
            "internal_blockers": list(internal),
            "evidence_blockers": list(evidence),
            "irreducible_external_information_proved": weak_external,
        },
    }


def strong_external_cert():
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


class OneShotRealityClosureV3Tests(unittest.TestCase):
    def test_old_weak_external_claim_is_demoted_to_internal_unsolved(self):
        c = closure(
            status="VERIFIED_FIXED_POINT__IRREDUCIBLE_EXTERNAL_INFORMATION_REQUIRED",
            passed=True,
            evidence=("MISSING_REPLAY_CONTEXT",),
            weak_external=True,
        )
        out = v3.compile_gap_contract(c)
        self.assertEqual(out["gap_class"], "INTERNAL_UNSOLVED__EXTERNALITY_NOT_PROVED")
        self.assertFalse(out["externality_gate"]["pass"])

    def test_reality_provider_cannot_run_on_weak_external_claim(self):
        c = closure(
            status="VERIFIED_FIXED_POINT__IRREDUCIBLE_EXTERNAL_INFORMATION_REQUIRED",
            passed=True,
            evidence=("MISSING_REPLAY_CONTEXT",),
            weak_external=True,
        )
        reality = unittest.mock.Mock()
        with patch.object(v3.v1, "run", return_value=c):
            out = v3.run(repo_root=".", reality_acquisition_provider=reality)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__INTERNAL_UNSOLVED__EXTERNALITY_ESCAPE_FORBIDDEN")
        reality.assert_not_called()

    def test_strong_information_theoretic_certificate_authorizes_reality_lane(self):
        c = closure(
            status="VERIFIED_FIXED_POINT__IRREDUCIBLE_EXTERNAL_INFORMATION_REQUIRED",
            passed=True,
            evidence=("MISSING_POLICY_CHANGING_BIT",),
            weak_external=True,
        )
        with patch.object(v3.v1, "run", return_value=c):
            out = v3.run(
                repo_root=".",
                externality_certificate_provider=lambda req: strong_external_cert(),
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__PROVEN_EXTERNAL_INFORMATION__REALITY_PROVIDER_REQUIRED")
        self.assertTrue(out["gap_contract"]["externality_gate"]["pass"])

    def test_empty_r3_queue_does_not_equal_terminal_goal_completion(self):
        c = closure(
            status="VERIFIED_INTERNAL_FIXED_POINT__IMPROVEMENT_QUEUE_EMPTY",
            passed=True,
        )
        out = v3.compile_gap_contract(c)
        self.assertEqual(out["gap_class"], "NO_R3_QUEUE_WORK__TERMINAL_MISSION_NOT_INFERRED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
