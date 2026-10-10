from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch
import unittest

from canonical.runtime import professional_r12_universal_positive_gate_totality_verified_v1 as v


class Tests(unittest.TestCase):
    def test_current_exact_composition_proves_cc_r3_only(self):
        out = v.verify()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["material_defeater_totality_proved"])
        self.assertTrue(out["cc_r3_terminal_closure_proved"])
        self.assertEqual(out["proof_basis"], "UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertFalse(out["semantic_property_truth_authority"])
        self.assertFalse(out["r4_proof_realization_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_missing_independent_receipt_truth_fails(self):
        original = v._load_json

        def altered(root, rel, expected):
            doc = deepcopy(dict(original(root, rel, expected)))
            if rel == v.RECEIPT_PATH:
                doc["truth"]["independent_verified"] = False
            return doc

        with patch.object(v, "_load_json", side_effect=altered):
            out = v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "INDEPENDENT_RECEIPT_TRUTH_DRIFT:independent_verified",
        )

    def test_failed_independent_replay_fails(self):
        original = v._load_json

        def altered(root, rel, expected):
            doc = deepcopy(dict(original(root, rel, expected)))
            if rel == v.RECEIPT_PATH:
                doc["independent_replay"]["tests_failed"] = 1
            return doc

        with patch.object(v, "_load_json", side_effect=altered):
            out = v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "INDEPENDENT_REPLAY_NOT_COMPLETE")

    def test_local_candidate_cannot_replace_independent_receipt(self):
        fake = v.candidate.verify()
        fake["independent_verified"] = True
        with patch.object(v.candidate, "verify", return_value=fake):
            out = v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "LOCAL_CANDIDATE_SELF_AUTHORIZED")

    def test_generator_closure_is_load_bearing(self):
        with patch.object(
            v.closure,
            "evaluate",
            return_value={
                "pass": False,
                "reason": "SYNTHETIC_REJECTION",
                "material_defeater_totality_proved": False,
                "cc_r3_terminal_closure_proved": False,
            },
        ):
            out = v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "GENERATOR_CLOSURE_REJECTED")

    def test_no_finite_catalog_or_cross_subject_authority(self):
        out = v.verify()
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["finite_catalog_only"])
        self.assertFalse(out["cross_subject_property_authority_transport"])
        self.assertFalse(out["semantic_property_truth_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
