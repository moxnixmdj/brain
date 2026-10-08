from __future__ import annotations

import unittest

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.opaque_goal_decision_envelope_v1 import compile_envelope


class OpaqueGoalDecisionEnvelopeV1Tests(unittest.TestCase):
    def test_every_raw_obligation_becomes_one_deterministic_opaque_atom(self):
        raw = compile_contract(
            "Create the report. Keep every unknown requirement.",
            source_id="user",
            routing_target_effects=["decision.adequate_action"],
        )
        out = compile_envelope(raw, context_id="ctx")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["obligation_count"], 2)
        self.assertEqual(
            set(out["opaque_remainder_atom_ids"]),
            set(raw["acceptance_contract"]["required_obligation_ids"]),
        )
        self.assertEqual(
            set(out["decision_basis"]),
            set(out["opaque_remainder_atom_ids"].values()),
        )
        self.assertTrue(out["sound_overapproximation"])
        self.assertFalse(out["semantic_completeness"])
        self.assertFalse(out["policy_adequacy_authority"])

    def test_compilation_is_deterministic(self):
        raw = compile_contract(
            "Do A. Do B.",
            source_id="user",
            routing_target_effects=["decision.adequate_action"],
        )
        left = compile_envelope(raw, context_id="ctx")
        right = compile_envelope(raw, context_id="ctx")
        self.assertEqual(left, right)

    def test_declared_discriminators_have_no_truth_authority(self):
        raw = compile_contract(
            "Do the useful thing.",
            source_id="user",
            routing_target_effects=["decision.adequate_action"],
        )
        out = compile_envelope(raw, context_id="ctx")
        self.assertTrue(out["pass"])
        self.assertTrue(out["candidate_discriminators"])
        self.assertTrue(
            all(
                row["truth_observation_authorized"] is False
                for row in out["candidate_discriminators"]
            )
        )

    def test_incomplete_raw_contract_fails_closed(self):
        out = compile_envelope(
            {
                "schema": "PROJECT_BRAIN_LOSSLESS_RAW_TASK_CONTRACT_V1",
                "pass": True,
                "nonwhitespace_source_coverage_complete": False,
            },
            context_id="ctx",
        )
        self.assertFalse(out["pass"])
        self.assertIn("RAW_SOURCE_COVERAGE_INCOMPLETE", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
