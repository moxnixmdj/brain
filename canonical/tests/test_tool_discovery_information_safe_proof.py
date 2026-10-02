from __future__ import annotations

import inspect
import json
import unittest

from canonical.runtime import tool_discovery_information_safe_candidate as candidate
from canonical.runtime import tool_discovery_information_safe_proof as proof


class ToolDiscoveryInformationSafeTests(unittest.TestCase):
    def test_hidden_capabilities_never_enter_public_payload(self):
        case = proof.generate_case(1234, 1)
        public = proof.public_stage(case, 1)
        self.assertNotIn("_oracle", public)
        text = json.dumps(public).lower()
        self.assertNotIn("epoch0", text)
        self.assertNotIn("epoch1", text)
        self.assertNotIn("hidden", text)

    def test_candidate_does_not_import_evaluator(self):
        src = inspect.getsource(candidate)
        self.assertNotIn("tool_discovery_information_safe_proof", src)
        self.assertNotIn("_oracle", src)

    def test_three_change_classes_pass(self):
        out = proof.run_batch(2026, 30, candidate.next_action)
        self.assertTrue(out["all_pass"], out)
        self.assertEqual(set(out["by_class"]), {
            "NO_CHANGE", "SELECTED_TOOL_LOSES_CAPABILITY", "CHEAPER_TOOL_GAINS_CAPABILITY"
        })

    def test_no_change_reuses_stage1_evidence(self):
        case = proof.generate_case(77, 0)  # NO_CHANGE
        result = proof.score_episode(case, candidate.next_action)
        self.assertTrue(result["pass"], result)
        self.assertEqual(result["stage2"]["probe_count"], 1)

    def test_selected_tool_loss_forces_reselection(self):
        case = proof.generate_case(77, 1)
        result = proof.score_episode(case, candidate.next_action)
        self.assertTrue(result["pass"], result)
        self.assertNotEqual(result["stage1"]["selected"], result["stage2"]["selected"])

    def test_cheaper_tool_gain_invalidates_old_negative(self):
        case = proof.generate_case(77, 2)
        result = proof.score_episode(case, candidate.next_action)
        self.assertTrue(result["pass"], result)
        self.assertNotEqual(result["stage1"]["selected"], result["stage2"]["selected"])
        self.assertLess(
            next(t["cost"] for t in case["tools"] if t["tool_id"] == result["stage2"]["selected"]),
            next(t["cost"] for t in case["tools"] if t["tool_id"] == result["stage1"]["selected"]),
        )

    def test_policy_that_selects_without_probing_fails(self):
        case = proof.generate_case(5, 0)
        def bad(public):
            return {"action": "SELECT", "tool_id": public["tools"][0]["tool_id"]}
        result = proof.score_episode(case, bad)
        self.assertFalse(result["pass"])

    def test_irrelevant_probe_fails(self):
        case = proof.generate_case(5, 0)
        def bad(public):
            return {"action": "PROBE", "tool_id": public["tools"][0]["tool_id"], "capability": "NOT_REQUIRED"}
        result = proof.score_episode(case, bad)
        self.assertFalse(result["pass"])
        self.assertIn("PROBE_IRRELEVANT_CAPABILITY", result["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
