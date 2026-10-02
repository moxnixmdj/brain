from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.research_t3_objective_binding_validator import validate


class ResearchT3ObjectiveBindingValidatorTests(unittest.TestCase):
    def test_live_binding_passes_pre_external_verification(self):
        root = Path(__file__).resolve().parents[2]
        out = validate(root)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["diagnostic_case_count"], 180)
        self.assertTrue(out["diagnostic_all_pass"])
        self.assertEqual(
            out["diagnostic_domains"],
            ["biology", "energy", "finance", "law", "materials", "systems"],
        )
        self.assertEqual(out["terminal_results_observed"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_binding_explicitly_disclaims_hle_score_equivalence(self):
        root = Path(__file__).resolve().parents[2]
        binding = json.loads(
            (root / "canonical/governance/RESEARCH_T3_OBJECTIVE_TERMINAL_BINDING_V1.json").read_text()
        )
        self.assertFalse(binding["acceptance"]["hle_score_equivalence_claimed"])
        self.assertFalse(binding["acceptance"]["hle_content_required_for_direct_objective_route"])
        self.assertIn("NOT_EXHAUSTIVE_PROOF", binding["source_pool"]["terminal_scope_claim"])

    def test_terminal_selector_is_post_freeze_only(self):
        root = Path(__file__).resolve().parents[2]
        binding = json.loads(
            (root / "canonical/governance/RESEARCH_T3_OBJECTIVE_TERMINAL_BINDING_V1.json").read_text()
        )
        selector = binding["selector"]
        self.assertFalse(selector["beacon_known_before_freeze"])
        self.assertFalse(selector["adaptive_case_selection"])
        self.assertFalse(selector["case_replacement"])
        self.assertFalse(selector["tuning_replay"])


if __name__ == "__main__":
    unittest.main()
