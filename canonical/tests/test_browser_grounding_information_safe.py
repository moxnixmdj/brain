from __future__ import annotations

import inspect
import json
import unittest

from canonical.runtime import browser_grounding_information_safe_candidate as candidate
from canonical.runtime import browser_grounding_information_safe_proof as proof


class BrowserGroundingInformationSafeTests(unittest.TestCase):
    def test_hidden_target_and_transition_not_public(self):
        case = proof.generate_case(17, 0)
        public = proof.public_state(case)
        self.assertNotIn("_oracle", public)
        raw = json.dumps(public, sort_keys=True).lower()
        self.assertNotIn("target_element_id", raw)
        self.assertNotIn("expected_terminal_state", raw)
        self.assertNotIn("force_first_target_mismatch", raw)

    def test_candidate_has_no_oracle_or_evaluator_dependency(self):
        src = inspect.getsource(candidate)
        self.assertNotIn("browser_grounding_information_safe_proof", src)
        self.assertNotIn("_oracle", src)

    def test_large_bounded_population(self):
        out = proof.run_batch(20261002, 360, candidate.next_action)
        self.assertTrue(out["all_pass"], out)

    def test_state_mismatch_requires_observed_recovery(self):
        case = next(
            proof.generate_case(91, i)
            for i in range(20)
            if proof.generate_case(91, i)["_oracle"]["force_first_target_mismatch"]
        )
        out = proof.run_episode(case, candidate.next_action)
        self.assertTrue(out["pass"], out)
        kinds = [x.get("receipt_kind") for x in out["history"]]
        self.assertIn("STATE_MISMATCH", kinds)
        self.assertIn("RECOVERY_APPLIED", kinds)
        self.assertEqual(kinds[-1], "STATE_ADVANCED")

    def test_wrong_target_fails(self):
        case = proof.generate_case(101, 1)
        wrong = next(
            x["element_id"] for x in case["initial_elements"]
            if x["element_id"] != case["_oracle"]["target_element_id"]
        )
        out = proof.run_episode(
            case,
            lambda public: {"action":"EXECUTE","element_id":wrong,"tool_action":"CLICK"},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "WRONG_TARGET_OR_ACTION")

    def test_goal_is_load_bearing_for_target_choice(self):
        case = proof.generate_case(7, 2)
        public = proof.public_state(case)
        original = candidate.next_action(public)
        self.assertEqual(original.get("element_id"), case["_oracle"]["target_element_id"])

        decoy = next(
            x for x in public["elements"]
            if x["element_id"] != case["_oracle"]["target_element_id"]
            and x.get("name")
        )
        mutated = dict(public)
        mutated["goal"] = f"Open {decoy['name']}."
        changed = candidate.next_action(mutated)
        self.assertEqual(changed.get("element_id"), decoy["element_id"])
        self.assertNotEqual(changed.get("element_id"), original.get("element_id"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
