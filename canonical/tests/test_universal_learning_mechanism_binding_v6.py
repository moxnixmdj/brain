from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GOV=ROOT/"canonical/governance/UNIVERSAL_LEARNING_MECHANISM_DISCOVERY_V6.json"

def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

class BindingTests(unittest.TestCase):
    def test_exact_v6_component_blobs(self):
        gov=json.loads(GOV.read_text(encoding="utf-8"))
        for rel,expected in gov["exact_bound_components"].items():
            with self.subTest(path=rel):
                self.assertEqual(blob_sha(ROOT/rel),expected)

    def test_v6_zero_credit_and_zero_authority(self):
        gov=json.loads(GOV.read_text(encoding="utf-8"))
        self.assertEqual(gov["acceptance_credit_delta"],0)
        self.assertEqual(gov["family_credit_delta"],0)
        self.assertEqual(gov["capability_credit_delta"],0)
        self.assertEqual(gov["ownership_credit_delta"],0)
        self.assertFalse(gov["execution_authority"])
        self.assertFalse(gov["promotion_authority"])
        self.assertFalse(gov["fresh_reality_authority"])

    def test_v5_verified_base_is_load_bearing(self):
        gov=json.loads(GOV.read_text(encoding="utf-8"))
        base=gov["verified_v5_base"]
        self.assertTrue(base["mandatory"])
        self.assertEqual(
            base["governance_git_blob_sha"],
            gov["exact_bound_components"]["canonical/governance/UNIVERSAL_LEARNING_RECURSIVE_ABSTRACTION_V5.json"],
        )
        self.assertEqual(
            base["verification_git_blob_sha"],
            gov["exact_bound_components"]["canonical/verification/UNIVERSAL_LEARNING_RECURSIVE_ABSTRACTION_V5_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"],
        )

    def test_unknown_domain_not_closed_by_v6(self):
        gov=json.loads(GOV.read_text(encoding="utf-8"))
        self.assertEqual(gov["causal_binding"]["effect"],"MECHANISM_ONLY__NO_DIRECT_LEAF_CLOSURE")
        self.assertIn("NO_UNKNOWN_DOMAIN_ACCEPTANCE_CREDIT",gov["hard_nonclaims"])

if __name__=="__main__":
    unittest.main(verbosity=2)
