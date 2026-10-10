from __future__ import annotations

import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_whole_leaf_scope_certificate_v1 as scope_verify


ROOT = Path(__file__).resolve().parents[2]
CLAIM_SCOPE_PATH = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_R10_EXECUTION_WHOLE_LEAF_CLAIM_SCOPE_20261010_V1.json"
CLAIM_VERIFY_PATH = ROOT / "canonical/verification/PROFESSIONAL_QUALITY_R10_EXECUTION_WHOLE_LEAF_CLAIM_SCOPE_VERIFY_20261010_V1.json"
CERT_PATH = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_R10_EXECUTION_WHOLE_LEAF_SCOPE_CERTIFICATE_20261010_V1.json"

CLAIM_SCOPE_BLOB = "8f95b72c6edc7ff307342f7a0513bb90e908cd4c"
CLAIM_VERIFY_BLOB = "44907b5d106db21e00648a234875ecc9e00e3364"


class R10ExecutionWholeLeafScopeCertificateTests(unittest.TestCase):
    def test_exact_current_r10_certificate_passes_scope_only(self):
        claim_scope=json.loads(CLAIM_SCOPE_PATH.read_text(encoding="utf-8"))
        claim_verify=json.loads(CLAIM_VERIFY_PATH.read_text(encoding="utf-8"))
        cert=json.loads(CERT_PATH.read_text(encoding="utf-8"))
        out=scope_verify.evaluate(
            claim_scope,
            claim_verify,
            cert,
            claim_scope_blob=CLAIM_SCOPE_BLOB,
            claim_verification_blob=CLAIM_VERIFY_BLOB,
            claim_verification_path="canonical/verification/PROFESSIONAL_QUALITY_R10_EXECUTION_WHOLE_LEAF_CLAIM_SCOPE_VERIFY_20261010_V1.json",
        )
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["whole_leaf_scope_complete"])
        self.assertEqual(
            out["claim_id"],
            "205a864e7d7a56a14a46bb75923cc9b11126d479676d26d88803831da1197294",
        )
        self.assertFalse(out["leaf_property_truth_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
