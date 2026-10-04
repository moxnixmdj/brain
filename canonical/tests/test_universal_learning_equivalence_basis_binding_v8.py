from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GOV=ROOT/"canonical/governance/UNIVERSAL_LEARNING_EQUIVALENCE_BASIS_V8.json"


def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


class UniversalLearningV8BindingTests(unittest.TestCase):
    def test_exact_bound_components_match(self):
        gov=json.loads(GOV.read_text(encoding="utf-8"))
        for rel,expected in gov["exact_bound_components"].items():
            with self.subTest(path=rel):
                self.assertEqual(blob_sha(ROOT/rel),expected)

    def test_v7_is_mandatory_base(self):
        gov=json.loads(GOV.read_text(encoding="utf-8"))
        base=gov["verified_v7_base"]
        self.assertTrue(base["mandatory"])
        self.assertEqual(base["governance_git_blob_sha"],"e26c8f4d8614720c1a45f28bcd2703dbb36bd980")
        self.assertEqual(base["verification_git_blob_sha"],"87f8660095b9a9d71eb160bf23616a46d4c3e1cf")
        self.assertEqual(base["activation_git_blob_sha"],"58cbfecea60e7f4259c5b7c0218ebc15c4e33399")

    def test_zero_credit_and_zero_authority(self):
        gov=json.loads(GOV.read_text(encoding="utf-8"))
        for key in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
            self.assertEqual(gov[key],0)
        self.assertFalse(gov["execution_authority"])
        self.assertFalse(gov["promotion_authority"])
        self.assertFalse(gov["fresh_reality_authority"])

    def test_no_universal_basis_or_equivalence_claim(self):
        gov=json.loads(GOV.read_text(encoding="utf-8"))
        claims=set(gov["hard_nonclaims"])
        self.assertIn("NO_UNIVERSAL_NOVELTY_BASIS_CLAIM",claims)
        self.assertIn("NO_UNIVERSAL_SYMMETRY_OR_EQUIVALENCE_CLASS_COMPLETENESS_CLAIM",claims)


if __name__=="__main__":
    unittest.main(verbosity=2)
