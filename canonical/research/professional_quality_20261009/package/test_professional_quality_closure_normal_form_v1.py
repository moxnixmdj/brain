from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.professional_quality_closure_normal_form_v1 import verify

ROOT = Path(__file__).resolve().parents[2]
NF = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_CLOSURE_NORMAL_FORM_20261009_V1.json"
CM = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_ADVERSARIAL_CHALLENGE_MATRIX_20261009_V1.json"

class TestProfessionalQualityClosureNormalFormV1(unittest.TestCase):
    def load(self):
        return json.loads(NF.read_text()), json.loads(CM.read_text())

    def test_current_candidate_is_structurally_closed_but_zero_credit(self):
        nf, cm = self.load()
        out = verify(nf, cm)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["root_count"], 12)
        self.assertEqual(out["challenge_count"], 28)
        self.assertEqual(out["covered_root_count"], 12)
        self.assertFalse(out["professional_quality_closed"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_missing_root_fails_closed(self):
        nf, cm = self.load()
        nf = copy.deepcopy(nf)
        nf["roots"] = nf["roots"][:-1]
        self.assertFalse(verify(nf, cm)["pass"])

    def test_unknown_challenge_root_fails_closed(self):
        nf, cm = self.load()
        cm = copy.deepcopy(cm)
        cm["challenges"][0]["root_ids"] = ["R999_FAKE"]
        self.assertFalse(verify(nf, cm)["pass"])

    def test_attack_cannot_expect_terminal_pass(self):
        nf, cm = self.load()
        cm = copy.deepcopy(cm)
        cm["challenges"][0]["expected_terminal_behavior"] = ["FAIL", "PASS"]
        self.assertFalse(verify(nf, cm)["pass"])

    def test_structural_manifest_cannot_claim_completeness(self):
        nf, cm = self.load()
        nf = copy.deepcopy(nf)
        nf["closure_rule"]["current_result"] = "PROVED"
        self.assertFalse(verify(nf, cm)["pass"])

if __name__ == "__main__":
    unittest.main()
