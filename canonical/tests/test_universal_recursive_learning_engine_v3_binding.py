from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "canonical/governance/UNIVERSAL_RECURSIVE_LEARNING_ENGINE_V3.json"


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class UniversalRecursiveLearningEngineV3BindingTests(unittest.TestCase):
    def test_every_bound_component_matches_exact_blob(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        for rel, expected in gov["exact_bound_components"].items():
            with self.subTest(path=rel):
                self.assertEqual(blob_sha(ROOT / rel), expected)

    def test_v3_is_additive_and_zero_credit(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        self.assertEqual(gov["extends"]["v1"], "canonical/governance/UNIVERSAL_LEARNING_CONTRACT_V1.json")
        self.assertEqual(gov["extends"]["v2_activation"], "canonical/governance/UNIVERSAL_LEARNING_ACTIVE_V2_ACTIVATION_V1.json")
        self.assertEqual(gov["acceptance_credit_delta"], 0)
        self.assertEqual(gov["family_credit_delta"], 0)
        self.assertEqual(gov["capability_credit_delta"], 0)
        self.assertEqual(gov["ownership_credit_delta"], 0)
        self.assertFalse(gov["execution_authority"])
        self.assertFalse(gov["promotion_authority"])
        self.assertFalse(gov["fresh_reality_authority"])

    def test_unknown_domain_bridge_is_not_acceptance_credit(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        self.assertEqual(
            gov["unknown_domain_bridge"]["status"],
            "STRUCTURAL_CANDIDATE_ONLY__SEPARATE_SCOPE_REDUCTION_REQUIRED",
        )
        self.assertIn(
            "FROZEN_UNKNOWN_DOMAIN_DIRECT_ORACLE_LEAF_SUCCESS",
            gov["unknown_domain_bridge"]["does_not_prove"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
