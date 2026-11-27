from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.finite_sample_ceiling_firewall_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]
REL = ROOT / "canonical/governance/RECOVERY_T0_T2_ACCEPTANCE_SCOPE_RELATION_V1.json"
SUPER = ROOT / "canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def recovery_witness():
    return {
        "id": "RECOVERY_T0_T2_ABSOLUTE_DOMINANCE_20261002_V1",
        "family": "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
        "mode": "ABSOLUTE_DOMINANCE",
        "verified": False,
        "independent": False,
        "contamination_clean": True,
        "binds_frozen_protocol": True,
        "scope_relation": "PROVEN_STRONGER",
        "closes_entire_protocol": True,
        "source_case_count": 60,
        "result": {
            "direction": "higher",
            "brain_lower_bound": 1.0,
            "theoretical_upper_bound": 1.0,
        },
    }


class Tests(unittest.TestCase):
    def test_live_recovery_candidate_is_not_a_protocol_wide_ceiling(self):
        out = evaluate(
            witness=recovery_witness(),
            relation=load(REL),
            target_superportfolio=load(SUPER),
        )
        self.assertFalse(out["pass"], out)
        self.assertIn("FINITE_SAMPLE_CANNOT_ESTABLISH_PROTOCOL_WIDE_CEILING", out["errors"])
        self.assertIn("SCOPE_RELATION_LACKS_COMPLETE_COVERAGE_PROOF", out["errors"])
        self.assertFalse(out["facts"]["target_case_generation_generated_now"])
        self.assertFalse(out["absolute_ceiling_established"])

    def test_universal_formal_scope_proof_can_cross_firewall(self):
        relation = copy.deepcopy(load(REL))
        relation["relation"] = "PROVEN_STRONGER"
        relation["universal_scope_proof"] = {
            "verified": True,
            "independent": True,
            "all_admissible_target_inputs_proved": True,
            "formal_completeness": True,
            "receipt": "canonical/verification/example_universal_scope_receipt.json",
        }
        out = evaluate(
            witness=recovery_witness(),
            relation=relation,
            target_superportfolio=load(SUPER),
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["basis"], "UNIVERSAL_FORMAL_SCOPE_PROOF")

    def test_exact_target_universe_cannot_be_claimed_before_target_generation(self):
        relation = copy.deepcopy(load(REL))
        relation["relation"] = "PROVEN_STRONGER"
        relation["target_case_universe_identity"] = {
            "verified": True,
            "independent": True,
            "relation": "EXACT",
            "complete_target_case_set": True,
            "receipt": "canonical/verification/example_exact_target_universe.json",
        }
        out = evaluate(
            witness=recovery_witness(),
            relation=relation,
            target_superportfolio=load(SUPER),
        )
        self.assertFalse(out["pass"], out)
        self.assertIn("EXACT_TARGET_UNIVERSE_CONTRADICTS_UNGENERATED_TARGET_PORTFOLIO", out["errors"])

    def test_exhaustive_finite_superset_can_cross_firewall(self):
        relation = copy.deepcopy(load(REL))
        relation["relation"] = "PROVEN_STRONGER"
        relation["exhaustive_finite_scope"] = {
            "verified": True,
            "independent": True,
            "exhaustive": True,
            "target_subset_proved": True,
            "receipt": "canonical/verification/example_exhaustive_scope_receipt.json",
        }
        out = evaluate(
            witness=recovery_witness(),
            relation=relation,
            target_superportfolio=load(SUPER),
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["basis"], "EXHAUSTIVE_FINITE_SUPERSET")


if __name__ == "__main__":
    unittest.main(verbosity=2)
