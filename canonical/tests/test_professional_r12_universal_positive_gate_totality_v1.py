from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
import unittest

from canonical.runtime import professional_r12_universal_positive_gate_totality_v1 as v


class Tests(unittest.TestCase):
    def test_exact_current_bytes_prove_candidate_only(self):
        out = v.verify()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["universal_positive_gate_totality_candidate_proved"])
        self.assertEqual(out["proof_basis"], "UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertTrue(out["scope_complete"])
        self.assertTrue(out["stable_c8_nonvacuity_separate_and_proved"])
        self.assertFalse(out["independent_verified"])
        self.assertFalse(out["cc_r3_terminal_closure_proved"])
        self.assertFalse(out["semantic_property_truth_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_target_obligation_is_positive_certification_safety(self):
        root = Path(__file__).resolve().parents[2]
        recon = json.loads((root / v.RECON_PATH).read_text(encoding="utf-8"))
        self.assertEqual(
            (recon["stronger_target_residual"])["obligation"],
            v.OBLIGATION,
        )
        self.assertIn("BEFORE_POSITIVE_CERTIFICATION", v.OBLIGATION)

    def test_stable_c8_is_required_separately(self):
        original = v._load

        def altered(root, rel, blob):
            doc = dict(original(root, rel, blob))
            if rel == v.C8_PATH:
                doc["consequence"] = dict(doc.get("consequence") or {})
                doc["consequence"]["r12_c8_nonvacuity_proved"] = False
            return doc

        with patch.object(v, "_load", side_effect=altered):
            out = v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "C8_NONVACUITY_NOT_PROVED")

    def test_independent_positive_gate_premise_is_load_bearing(self):
        original = v._load

        def altered(root, rel, blob):
            doc = dict(original(root, rel, blob))
            if rel == v.V9_VERIFY_PATH:
                doc["proves"] = [
                    x for x in (doc.get("proves") or [])
                    if x != v.V9_PROOF_SENTENCE
                ]
            return doc

        with patch.object(v, "_load", side_effect=altered):
            out = v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "V9_UNIVERSAL_POSITIVE_GATE_PREMISE_NOT_INDEPENDENTLY_PROVED",
        )

    def test_lossy_or_narrow_carrier_fails_closed(self):
        original = v._load

        def altered(root, rel, blob):
            doc = dict(original(root, rel, blob))
            if rel == v.IDENTITY_PATH:
                doc["theorem"] = dict(doc.get("theorem") or {})
                doc["theorem"]["semantic_information_loss"] = True
            return doc

        with patch.object(v, "_load", side_effect=altered):
            out = v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "IDENTITY_CARRIER_LOSSY")

    def test_local_candidate_cannot_self_mint_cc_r3(self):
        out = v.verify()
        for key in (
            "independent_verified",
            "cc_r3_terminal_closure_proved",
            "semantic_property_truth_authority",
            "r4_proof_realization_authority",
            "quality_authority",
            "acceptance_authority",
            "promotion_authority",
            "terminal_authority",
        ):
            self.assertFalse(out[key], key)

    def test_finite_catalog_is_explicitly_not_basis(self):
        out = v.verify()
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["finite_catalog_only"])
        self.assertFalse(out["eight_clause_count_only"])
        self.assertEqual(out["unknown_remainder"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
