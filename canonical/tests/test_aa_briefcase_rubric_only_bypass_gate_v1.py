from __future__ import annotations

import unittest

from canonical.runtime.aa_briefcase_rubric_only_bypass_gate_v1 import (
    RubricBypassError,
    evaluate,
)


class Tests(unittest.TestCase):
    def base(self):
        return {
            "target": "AA-Briefcase v1.1 >= 1822 Elo",
            "public_three_scope_semantics_bound": True,
            "rubric_only_certificate": False,
            "sound_rubric_only_headline_elo_lower_bound_ge_1822": False,
            "analytical_quality_score_bearing_state_bound": False,
            "presentation_score_bearing_state_bound": False,
        }

    def test_rubric_only_without_headline_bound_rejected(self):
        x = self.base()
        x["rubric_only_certificate"] = True
        out = evaluate(x)
        self.assertEqual(out["status"], "REJECT_RUBRIC_ONLY_BYPASS")
        self.assertFalse(out["pass"])

    def test_caller_asserted_headline_bound_is_not_self_authenticating(self):
        x = self.base()
        x["rubric_only_certificate"] = True
        x["sound_rubric_only_headline_elo_lower_bound_ge_1822"] = True
        out = evaluate(x)
        self.assertEqual(
            out["status"], "RUBRIC_ONLY_BYPASS_THEOREM_REQUIRED_UPSTREAM"
        )
        self.assertFalse(out["pass"])

    def test_three_scope_state_routes_to_trace_gate(self):
        x = self.base()
        x["analytical_quality_score_bearing_state_bound"] = True
        x["presentation_score_bearing_state_bound"] = True
        out = evaluate(x)
        self.assertEqual(
            out["status"], "THREE_SCOPE_INFORMATION_PRESENT__CONTINUE_SCORE_TRACE_ROUTE"
        )

    def test_missing_pairwise_scopes_are_explicit(self):
        out = evaluate(self.base())
        self.assertEqual(
            out["missing"],
            [
                "ANALYTICAL_QUALITY_SCORE_BEARING_STATE",
                "PRESENTATION_SCORE_BEARING_STATE",
            ],
        )

    def test_public_semantics_must_be_bound(self):
        x = self.base()
        x["public_three_scope_semantics_bound"] = False
        with self.assertRaisesRegex(
            RubricBypassError, "PUBLIC_THREE_SCOPE_SEMANTICS_UNBOUND"
        ):
            evaluate(x)


if __name__ == "__main__":
    unittest.main(verbosity=2)
