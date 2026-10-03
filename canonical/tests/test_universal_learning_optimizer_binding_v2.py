from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from canonical.runtime import universal_learning_optimizer_v2 as opt

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "canonical/governance/UNIVERSAL_LEARNING_OPTIMIZER_V2.json"


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class UniversalLearningOptimizerBindingV2Tests(unittest.TestCase):
    def test_every_bound_component_matches_exact_blob(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        for rel, expected in gov["exact_bound_components"].items():
            with self.subTest(path=rel):
                self.assertEqual(blob_sha(ROOT / rel), expected)

    def test_v1_is_mandatory_and_v2_is_strictly_optimization_only(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        self.assertTrue(gov["v1_safety_authority"]["mandatory"])
        self.assertEqual(
            gov["v1_safety_authority"]["contract_path"],
            "canonical/runtime/universal_learning_contract_v1.py",
        )
        self.assertIn(
            "NO_V2_ROUTE_MAY_BYPASS_V1_VERIFICATION_OR_PROMOTION_GATES",
            gov["hard_rules"],
        )
        self.assertIn(
            "NO_CLAIM_THAT_OPTIMAL_CONTROL_IMPLIES_UNIVERSAL_SEMANTIC_SUCCESS",
            gov["hard_nonclaims"],
        )

    def test_optimizer_theorem_preserves_zero_credit_boundary(self):
        out = opt.prove_optimizer_invariants()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["v1_required_as_safety_gate"])
        self.assertFalse(out["semantic_success_rate_proved"])
        self.assertFalse(out["unknown_domain_acceptance_proved"])
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["ownership_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])

    def test_required_v2_mechanisms_are_declared(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        required = {
            "MINIMUM_NOVELTY_DELTA",
            "VERIFIED_TRANSFER_ADMISSION",
            "CONSERVATIVE_ACTION_VALUE_SELECTION",
            "DECISION_SUFFICIENT_STOPPING",
            "DEPENDENCY_CONE_INVALIDATION",
            "VERIFIED_EPISODE_META_LEARNING",
        }
        self.assertEqual(set(gov["optimizer_mechanisms"]), required)


if __name__ == "__main__":
    unittest.main(verbosity=2)
