from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from canonical.runtime import universal_active_transfer_learner_v2 as v2

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "canonical/governance/UNIVERSAL_ACTIVE_TRANSFER_LEARNER_V2.json"


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class UniversalActiveTransferLearnerV2BindingTests(unittest.TestCase):
    def test_every_bound_component_matches_exact_blob(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        for rel, expected in gov["exact_bound_components"].items():
            with self.subTest(path=rel):
                self.assertEqual(blob_sha(ROOT / rel), expected)

    def test_v2_extends_v1_and_cannot_replace_verified_base(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        self.assertEqual(
            gov["extends_verified_base"],
            "canonical/governance/UNIVERSAL_LEARNING_CONTRACT_V1.json",
        )
        self.assertTrue(gov["v1_remains_authoritative_for_unknown_capture_and_promotion_safety"])

    def test_governance_preserves_zero_credit_boundary(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        self.assertEqual(gov["acceptance_credit_delta"], 0)
        self.assertEqual(gov["ownership_credit_delta"], 0)
        self.assertFalse(gov["execution_authority"])
        self.assertFalse(gov["promotion_authority"])
        self.assertIn("NO_UNIVERSAL_SEMANTIC_SUCCESS_CLAIM", gov["hard_nonclaims"])
        self.assertIn("NO_UNKNOWN_DOMAIN_ACCEPTANCE_CREDIT_FROM_V2_ALONE", gov["hard_nonclaims"])

    def test_runtime_surface_exposes_all_v2_optimizations(self):
        required = {
            "minimum_novelty_delta",
            "rank_learning_actions",
            "update_hypotheses",
            "decision_sufficient",
            "invalidation_cone",
            "compile_verified_skill",
            "compile_learning_strategy",
            "learning_episode",
        }
        self.assertTrue(all(hasattr(v2, name) for name in required))


if __name__ == "__main__":
    unittest.main(verbosity=2)
