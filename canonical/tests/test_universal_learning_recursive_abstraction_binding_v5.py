from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from canonical.runtime import universal_learning_recursive_abstraction_router_v5 as v5

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "canonical/governance/UNIVERSAL_LEARNING_RECURSIVE_ABSTRACTION_V5.json"


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class UniversalLearningRecursiveAbstractionBindingV5Tests(unittest.TestCase):
    def test_every_exact_bound_component_matches(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        for rel, expected in gov["exact_bound_components"].items():
            with self.subTest(path=rel):
                self.assertEqual(blob_sha(ROOT / rel), expected)

    def test_v4_verified_base_is_load_bearing(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        base = gov["verified_v4_base"]
        self.assertTrue(base["mandatory"])
        self.assertEqual(
            base["governance_path"],
            "canonical/governance/UNIVERSAL_LEARNING_OPEN_WORLD_ROUTER_V4.json",
        )
        self.assertEqual(
            base["verification_path"],
            "canonical/verification/UNIVERSAL_LEARNING_OPEN_WORLD_V4_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
        )
        self.assertIn(
            "V5_MAY_NOT_WEAKEN_V4_OPEN_WORLD_FALSE_CONSENSUS_OR_PROBE_SAFETY_GUARDS",
            gov["hard_rules"],
        )

    def test_v5_theorem_preserves_zero_credit_boundary(self):
        out = v5.prove_v5_invariants()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["v4_open_world_guard_preserved"])
        self.assertTrue(out["dependency_superset_pruning_sound"])
        self.assertTrue(out["abstraction_induction_candidate_only"])
        self.assertTrue(out["minimax_primary_order_preserved"])
        self.assertFalse(out["semantic_success_rate_proved"])
        self.assertFalse(out["unknown_domain_acceptance_proved"])
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["ownership_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])

    def test_v5_improvements_are_exactly_the_new_scope(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        self.assertEqual(
            set(gov["v5_improvements"]),
            {
                "PROOF_CARRYING_DEPENDENCY_SUPERSET_COMPRESSION",
                "RECURSIVE_VERIFIED_SKILL_ABSTRACTION_INDUCTION",
                "MINIMAX_FIRST_COMPOUNDING_PROBE_TIEBREAK",
            },
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
