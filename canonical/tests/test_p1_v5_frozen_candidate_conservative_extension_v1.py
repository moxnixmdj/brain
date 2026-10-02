from __future__ import annotations

import copy
import unittest

from canonical.runtime import p1_v5_frozen_candidate_conservative_extension_v1 as bridge


class Tests(unittest.TestCase):
    def test_live_complete_semantic_quotient_passes(self):
        out = bridge.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["proof_scope"]["complete_semantic_class_count"], 30)
        self.assertEqual(out["proof_scope"]["checked_rows"], 60)
        self.assertEqual(out["proof_scope"]["seed_values_consumed"], 0)
        self.assertEqual(out["proof_scope"]["terminal_case_ids_consumed"], 0)
        self.assertFalse(out["candidate_identity"]["byte_identical"])
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])

    def test_every_difficulty_cause_class_matches_old_output(self):
        seen = set()
        for difficulty in range(1, 6):
            n = bridge._legacy_n(difficulty)
            for cause in range(1, n - 2):
                row = bridge.check_structural_class(difficulty, cause)
                self.assertTrue(row["legacy_pass"], row)
                self.assertTrue(row["translated_v5_pass"], row)
                self.assertTrue(row["outputs_equal"], row)
                self.assertEqual(row["v5_status"], "IDENTIFIED")
                seen.add((difficulty, cause))
        self.assertEqual(len(seen), 30)

    def test_repair_order_is_nonsemantic_for_all_structural_classes(self):
        for difficulty in range(1, 6):
            n = bridge._legacy_n(difficulty)
            for cause in range(1, n - 2):
                a = bridge.check_structural_class(difficulty, cause, reverse_repairs=False)
                b = bridge.check_structural_class(difficulty, cause, reverse_repairs=True)
                self.assertEqual(a["legacy_output"], b["legacy_output"])
                self.assertEqual(a["translated_v5_output"], b["translated_v5_output"])

    def test_nonmonotonic_failure_is_rejected(self):
        case = bridge.structural_case(3, 3)
        public = bridge.legacy_suite.public_task(case)
        public = copy.deepcopy(public)
        public["task"]["trajectory"][4]["invariant_pass"] = True
        with self.assertRaises(bridge.BridgeError):
            bridge.embed_legacy_public_to_v5(public)

    def test_missing_unique_cause_repair_is_rejected(self):
        case = bridge.structural_case(2, 2)
        public = bridge.legacy_suite.public_task(case)
        public = copy.deepcopy(public)
        public["task"]["repair_candidates"] = [
            x for x in public["task"]["repair_candidates"] if x["targets_step"] != 2
        ]
        with self.assertRaises(bridge.BridgeError):
            bridge.embed_legacy_public_to_v5(public)

    def test_v5_downstream_or_wrong_mechanism_cannot_translate(self):
        case = bridge.structural_case(4, 2)
        public = bridge.legacy_suite.public_task(case)
        typed = bridge.embed_legacy_public_to_v5(public)
        out = bridge.v5_candidate.solve(typed)
        bad = copy.deepcopy(out)
        bad["cause_action_id"] = "A3"
        bad["cause_action_ids"] = ["A3"]
        bad["critical_action_id"] = "A3"
        bad["repair_targets"] = ["restore:A3:INVARIANT"]
        with self.assertRaises(bridge.BridgeError):
            bridge.translate_v5_to_legacy(public, bad)

        bad2 = copy.deepcopy(out)
        bad2["mechanism_classes"] = ["AUTHORITY"]
        with self.assertRaises(bridge.BridgeError):
            bridge.translate_v5_to_legacy(public, bad2)

    def test_bridge_does_not_read_terminal_result_or_seed(self):
        out = bridge.evaluate()
        forbidden = " ".join(out["forbidden_inference"])
        self.assertIn("DOES_NOT_REPLAY", forbidden)
        self.assertEqual(out["terminal_results_replayed"], 0)
        self.assertEqual(out["new_reality_units_consumed"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
