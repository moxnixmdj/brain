from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GOV=ROOT/"canonical/governance/UNIVERSAL_RECURSIVE_LEARNING_ENGINE_V3.json"

def blob_sha(path: Path) -> str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

class BindingTests(unittest.TestCase):
    def test_exact_components_match(self):
        gov=json.loads(GOV.read_text())
        for rel,expected in gov["exact_bound_components"].items():
            with self.subTest(path=rel):
                self.assertEqual(blob_sha(ROOT/rel),expected)

    def test_v3_extends_active_v2_and_preserves_authority(self):
        gov=json.loads(GOV.read_text())
        self.assertEqual(gov["extends_active_base"],"canonical/governance/UNIVERSAL_LEARNING_ACTIVE_V2_ACTIVATION_V1.json")
        self.assertEqual(gov["authoritative_trust_layer"],"V1_THROUGH_ACTIVE_V2_ROUTER")
        self.assertEqual(gov["acceptance_credit_delta"],0)
        self.assertEqual(gov["ownership_credit_delta"],0)

    def test_unknown_domain_claim_is_residual_reduction_only(self):
        gov=json.loads(GOV.read_text())
        self.assertFalse(gov["unknown_domain_relation"]["acceptance_proved"])
        self.assertIn("TARGET_DOMAIN_TERMINAL_SUCCESS_REMAINS_UNPROVED",gov["hard_nonclaims"])
        self.assertIn("HYPOTHESIS_AND_PROBE_MODEL_COMPLETENESS_IS_NOT_ASSUMED",gov["hard_nonclaims"])

if __name__=="__main__":
    unittest.main(verbosity=2)
