from __future__ import annotations

import unittest

from canonical.runtime import p1_scope_rescue_supplement_v1 as supplement


class P1ScopeRescueSupplementTests(unittest.TestCase):
    def test_full_frozen_semantic_cross_product(self):
        out = supplement.run_suite(123456789)
        self.assertTrue(out["pass"], out["failures"][:1])
        self.assertEqual(out["case_count"], 6 * 8 * 2)
        self.assertEqual(out["dimensions"]["domains"], sorted(supplement.DOMAINS))
        self.assertEqual(out["dimensions"]["kinds"], sorted(supplement.KINDS))
        self.assertEqual(out["dimensions"]["patterns"], ["IDENTIFIED", "INTERACTION"])
        self.assertGreater(out["explicit_scope_cases"], 0)
        self.assertEqual(out["candidate_terminal_rescue_passes"], out["case_count"])
        self.assertEqual(out["symptom_only_negative_control_passes"], out["case_count"])
        self.assertFalse(out["terminal_v3_replayed"])
        self.assertEqual(out["incremental_spend_usd"], 0)

    def test_scope_is_first_class_mechanism(self):
        case = supplement.generate_case(
            17,
            domain="BROWSER",
            kind="SCOPE",
            pattern="DELAYED",
        )
        public = supplement.public_task(case)
        out = supplement.candidate_v5.solve(public)
        self.assertEqual(out["mechanism_classes"], ["SCOPE"])
        self.assertIn(":SCOPE", out["repair_targets"][0])
        self.assertTrue(supplement.score_case(case, out)["pass"])

    def test_symptom_only_repair_cannot_rescue(self):
        case = supplement.generate_case(
            23,
            domain="CODE",
            kind="PROVENANCE",
            pattern="DELAYED",
        )
        symptom = case["_oracle"]["symptom_actions"][0]
        verdict = supplement.apply_intervention(case, [f"restore:{symptom}:INVARIANT"])
        self.assertFalse(verdict["terminal_pass"])

    def test_interaction_requires_all_root_repairs(self):
        case = supplement.generate_case(
            29,
            domain="RESEARCH",
            kind="SCOPE",
            pattern="INTERACTION",
        )
        out = supplement.candidate_v5.solve(supplement.public_task(case))
        verdict = supplement.score_case(case, out)
        self.assertTrue(verdict["pass"], verdict)
        self.assertTrue(verdict["partial_interaction_controls"])
        self.assertTrue(all(not x["terminal_pass"] for x in verdict["partial_interaction_controls"]))

    def test_hidden_oracle_never_enters_public_payload(self):
        case = supplement.generate_case(
            31,
            domain="TOOL_API",
            kind="TOOL_CONTRACT",
            pattern="INTERACTION",
        )
        public = supplement.public_task(case)
        self.assertNotIn("_oracle", public)
        self.assertNotIn("repair_targets", repr(public))


if __name__ == "__main__":
    unittest.main(verbosity=2)
