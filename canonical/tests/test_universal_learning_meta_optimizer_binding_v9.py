from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GOV=ROOT/"canonical/governance/UNIVERSAL_LEARNING_META_OPTIMIZER_V9.json"


def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


class UniversalLearningV9BindingTests(unittest.TestCase):
    def test_exact_bound_components_match(self):
        gov=json.loads(GOV.read_text(encoding="utf-8"))
        for rel,expected in gov["exact_bound_components"].items():
            with self.subTest(path=rel):
                self.assertEqual(blob_sha(ROOT/rel),expected)

    def test_verified_v8_base_exact(self):
        gov=json.loads(GOV.read_text(encoding="utf-8"))
        base=gov["verified_v8_base"]
        self.assertTrue(base["mandatory"])
        self.assertEqual(base["governance_git_blob_sha"],"095dc93747a64a95feb001f1ecca4714ad666b72")
        self.assertEqual(base["verification_git_blob_sha"],"0f7e3b6fc1e24e5f87af75cc95c9d402cf141cf0")

    def test_meta_substrate_exact(self):
        gov=json.loads(GOV.read_text(encoding="utf-8"))
        self.assertEqual(
            gov["existing_meta_substrate"]["git_blob_sha"],
            "d9aab2f0b269806118fe82f47e516b867c6c071c",
        )

    def test_zero_credit_and_no_universal_strategy_claim(self):
        gov=json.loads(GOV.read_text(encoding="utf-8"))
        for key in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
            self.assertEqual(gov[key],0)
        self.assertFalse(gov["execution_authority"])
        self.assertFalse(gov["promotion_authority"])
        self.assertFalse(gov["fresh_reality_authority"])
        self.assertIn("NO_UNIVERSAL_BEST_LEARNING_STRATEGY_CLAIM",set(gov["hard_nonclaims"]))
        self.assertIn("NO_ABOVE_EXPONENTIAL_GROWTH_GUARANTEE",set(gov["hard_nonclaims"]))


if __name__=="__main__":
    unittest.main(verbosity=2)
