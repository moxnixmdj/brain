import unittest
from canonical.runtime.cursorbench_anchor_transfer_certificate_v1 import (
    CertificateError, verify_anchor_transfer
)

SHA = "0" * 64

def base(route):
    return {
        "benchmark": "CURSORBENCH_4_0",
        "anchor_model": "OPUS_5_5_MAX",
        "anchor_score": 0.578,
        "route": route,
        "evidence": [{"sha256": SHA}],
    }

class CursorBenchAnchorTransferTests(unittest.TestCase):
    def test_direct_578_passes(self):
        c = base("DIRECT_BRAIN_SCORE_LOWER_BOUND")
        c["brain_score_lower_bound"] = 0.578
        self.assertTrue(verify_anchor_transfer(c)["threshold_met"])

    def test_direct_577_fails(self):
        c = base("DIRECT_BRAIN_SCORE_LOWER_BOUND")
        c["brain_score_lower_bound"] = 0.577
        self.assertFalse(verify_anchor_transfer(c)["threshold_met"])

    def test_noninferiority_requires_same_evaluator(self):
        c = base("TARGET_SCOPED_SCORE_NONINFERIORITY")
        c["brain_score_ge_anchor_score"] = True
        c["same_frozen_evaluator_relation"] = False
        self.assertFalse(verify_anchor_transfer(c)["threshold_met"])

    def test_noninferiority_passes_when_bound(self):
        c = base("TARGET_SCOPED_SCORE_NONINFERIORITY")
        c["brain_score_ge_anchor_score"] = True
        c["same_frozen_evaluator_relation"] = True
        self.assertTrue(verify_anchor_transfer(c)["threshold_met"])

    def test_exact_input_equivalence_passes(self):
        c = base("COMPLETE_SCORE_INPUT_EQUIVALENCE")
        c["same_frozen_score_functional"] = True
        c["complete_score_relevant_input_equivalence"] = True
        self.assertTrue(verify_anchor_transfer(c)["threshold_met"])

    def test_input_dominance_without_monotonicity_fails(self):
        c = base("INPUT_DOMINANCE_WITH_MONOTONICITY")
        c["same_frozen_score_functional"] = True
        c["complete_score_relevant_input_dominance"] = True
        c["score_functional_monotonicity_proved"] = False
        self.assertFalse(verify_anchor_transfer(c)["threshold_met"])

    def test_input_dominance_with_monotonicity_passes(self):
        c = base("INPUT_DOMINANCE_WITH_MONOTONICITY")
        c["same_frozen_score_functional"] = True
        c["complete_score_relevant_input_dominance"] = True
        c["score_functional_monotonicity_proved"] = True
        self.assertTrue(verify_anchor_transfer(c)["threshold_met"])

    def test_requires_content_addressed_evidence(self):
        c = base("TARGET_SCOPED_SCORE_NONINFERIORITY")
        c["same_frozen_evaluator_relation"] = True
        c["brain_score_ge_anchor_score"] = True
        c["evidence"] = []
        with self.assertRaisesRegex(CertificateError, "CONTENT_ADDRESSED_EVIDENCE_REQUIRED"):
            verify_anchor_transfer(c)

    def test_wrong_anchor_rejected(self):
        c = base("TARGET_SCOPED_SCORE_NONINFERIORITY")
        c["anchor_score"] = 0.579
        with self.assertRaisesRegex(CertificateError, "ANCHOR_SCORE_MUST_EQUAL_0_578"):
            verify_anchor_transfer(c)

if __name__ == "__main__":
    unittest.main()
