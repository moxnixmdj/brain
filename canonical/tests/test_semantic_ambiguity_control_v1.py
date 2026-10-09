import unittest

from canonical.runtime.semantic_ambiguity_control_v1 import decide


class Tests(unittest.TestCase):
    def test_terminally_equivalent_ambiguity_needs_no_clarification(self):
        out = decide({
            "ambiguity_owner": "USER_INTENT",
            "hypothesis_set_complete": True,
            "worlds": [
                {
                    "world_id": "alice",
                    "terminal_signature_complete": True,
                    "terminal_signature": {"action": "SEND_SAME_PUBLIC_NOTICE"},
                },
                {
                    "world_id": "sarah",
                    "terminal_signature_complete": True,
                    "terminal_signature": {"action": "SEND_SAME_PUBLIC_NOTICE"},
                },
            ],
            "observations": [],
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["action"], "CONTINUE_WITHOUT_DISAMBIGUATION")
        self.assertFalse(out["ask_user_required"])
        self.assertTrue(out["terminally_equivalent"])

    def test_action_relevant_user_ambiguity_without_separator_asks_minimally(self):
        out = decide({
            "ambiguity_owner": "USER_INTENT",
            "hypothesis_set_complete": True,
            "worlds": [
                {
                    "world_id": "alice",
                    "terminal_signature_complete": True,
                    "terminal_signature": {"recipient": "ALICE"},
                },
                {
                    "world_id": "sarah",
                    "terminal_signature_complete": True,
                    "terminal_signature": {"recipient": "SARAH"},
                },
            ],
            "observations": [],
        })
        self.assertFalse(out["pass"])
        self.assertTrue(out["ask_user_required"])
        self.assertEqual(out["action"], "ASK_USER_MINIMUM_CLARIFICATION")
        self.assertIn("UNDERDETERMINATION", out["status"])

    def test_contextual_separator_is_preferred_to_user_question(self):
        out = decide({
            "ambiguity_owner": "USER_INTENT",
            "hypothesis_set_complete": True,
            "worlds": [
                {
                    "world_id": "alice",
                    "terminal_signature_complete": True,
                    "terminal_signature": {"recipient": "ALICE"},
                },
                {
                    "world_id": "sarah",
                    "terminal_signature_complete": True,
                    "terminal_signature": {"recipient": "SARAH"},
                },
            ],
            "observations": [
                {
                    "observation_id": "reuse_prior_turn_binding",
                    "cost_units": 0,
                    "outcome_map_complete": True,
                    "outcomes": {
                        "alice": "prior_turn_names_alice",
                        "sarah": "prior_turn_names_sarah",
                    },
                }
            ],
        })
        self.assertFalse(out["pass"])
        self.assertFalse(out["ask_user_required"])
        self.assertEqual(
            out["action"],
            "ACQUIRE_MINIMUM_TERMINALLY_RELEVANT_DISCRIMINATOR",
        )
        self.assertEqual(out["next_observation_id"], "reuse_prior_turn_binding")

    def test_external_world_underdetermination_does_not_ask_user_for_unknown_fact(self):
        out = decide({
            "ambiguity_owner": "EXTERNAL_WORLD",
            "hypothesis_set_complete": True,
            "worlds": [
                {
                    "world_id": "w1",
                    "terminal_signature_complete": True,
                    "terminal_signature": {"action": "A"},
                },
                {
                    "world_id": "w2",
                    "terminal_signature_complete": True,
                    "terminal_signature": {"action": "B"},
                },
            ],
            "observations": [],
        })
        self.assertFalse(out["pass"])
        self.assertFalse(out["ask_user_required"])
        self.assertEqual(
            out["action"],
            "ABSTAIN_OR_ACQUIRE_STRONGER_AUTHENTIC_INFORMATION",
        )

    def test_incomplete_hypothesis_set_is_not_mislabeled_as_underdetermined(self):
        out = decide({
            "ambiguity_owner": "USER_INTENT",
            "hypothesis_set_complete": False,
            "worlds": [
                {
                    "world_id": "w1",
                    "terminal_signature_complete": True,
                    "terminal_signature": {"action": "A"},
                }
            ],
            "observations": [],
        })
        self.assertFalse(out["pass"])
        self.assertFalse(out["ask_user_required"])
        self.assertEqual(out["status"], "FAIL_CLOSED__AMBIGUITY_MODEL_INSUFFICIENT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
