from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V1.json"

REQUIRED_STEPS = {
    "COMPILE_TARGET_SPEC_AND_HARD_CONSTRAINTS",
    "GENERATE_DIVERSE_CANDIDATE_BRANCHES_WITH_INCUMBENT_PRESERVATION",
    "RUN_DETERMINISTIC_FACT_STRUCTURE_FORMAT_AND_GROUNDING_CHECKS",
    "RENDER_EXACT_AUDIENCE_VIEW_AND_BIND_OBSERVATION_CHANNELS",
    "RUN_CRITERION_SPECIFIC_PLUS_HOLISTIC_COMPARATIVE_EVALUATION",
    "ATTACK_FINALISTS_WITH_RELEVANT_INVARIANCE_DEFEATER_HIDDEN_CHANNEL_AND_COUNTEREXAMPLE_PROBES",
    "FREEZE_WINNER_AND_USE_FRESH_OR_SELECTION_AWARE_TERMINAL_EVIDENCE",
    "ISSUE_SCOPED_CERTIFICATE_OR_ABSTAIN_WITH_MINIMUM_BLOCKING_CUT",
}

class TestProfessionalQualityP1ExecutionProfileV1(unittest.TestCase):
    def test_profile_is_complete_lightweight_and_zero_credit(self):
        p = json.loads(PROFILE.read_text())
        self.assertEqual(p["status"], "CANDIDATE_EXECUTION_POLICY__ZERO_REALITY__ZERO_CREDIT")
        self.assertEqual(set(p["steps"]), REQUIRED_STEPS)
        self.assertTrue(p["escalation_triggers"])
        self.assertIn("DO_NOT_RUN_ALL_DEEP_ASSURANCE_MACHINERY", p["default_non_escalation_rule"])
        self.assertIn("MATERIALLY_DISTINCT_FALSE_CERTIFICATION_CAUSAL_PATH", p["new_root_rule"])
        self.assertIn("NO_PROFESSIONAL_QUALITY_COMPLETENESS_PROOF", p["hard_nonclaims"])
        self.assertEqual(p["accounting"]["fresh_target_reality_units_consumed"], 0)
        self.assertEqual(p["accounting"]["terminal_credit_delta"], 0)
        self.assertEqual(p["accounting"]["capability_credit_delta"], 0)

if __name__ == "__main__":
    unittest.main()
