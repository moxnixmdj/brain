from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GOV=ROOT/"canonical/governance/UNIVERSAL_LEARNING_PROOF_PROGRAM_V7.json"


def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


class UniversalLearningProofProgramV7BindingTests(unittest.TestCase):
    def test_every_bound_component_matches_exact_blob(self):
        gov=json.loads(GOV.read_text(encoding="utf-8"))
        for rel,expected in gov["exact_bound_components"].items():
            with self.subTest(path=rel):
                self.assertEqual(blob_sha(ROOT/rel),expected)

    def test_v6_base_is_load_bearing(self):
        gov=json.loads(GOV.read_text(encoding="utf-8"))
        base=gov["verified_v6_base"]
        self.assertTrue(base["mandatory"])
        self.assertEqual(base["governance_git_blob_sha"],"65e291e3afebbf3547771ee580104361d1920788")
        self.assertEqual(base["verification_git_blob_sha"],"ff590a8f40b891d3c53bb2c50cd679bb0dd42c72")

    def test_zero_credit_and_zero_authority(self):
        gov=json.loads(GOV.read_text(encoding="utf-8"))
        self.assertEqual(gov["acceptance_credit_delta"],0)
        self.assertEqual(gov["family_credit_delta"],0)
        self.assertEqual(gov["capability_credit_delta"],0)
        self.assertEqual(gov["ownership_credit_delta"],0)
        self.assertFalse(gov["execution_authority"])
        self.assertFalse(gov["promotion_authority"])
        self.assertFalse(gov["fresh_reality_authority"])

    def test_no_self_generated_program_proof_claim(self):
        gov=json.loads(GOV.read_text(encoding="utf-8"))
        self.assertIn("NO_SELF_GENERATED_PROGRAM_PROOF",gov["hard_nonclaims"])
        self.assertIn(
            "INDUCED_EXECUTABLE_PROGRAM_IS_CANDIDATE_ONLY_UNTIL_SEPARATELY_VERIFIED",
            gov["hard_rules"],
        )


if __name__=="__main__":
    unittest.main(verbosity=2)
