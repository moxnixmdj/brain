from __future__ import annotations

import unittest

from canonical.runtime.source_aligned_regcap_context_proof_v1 import (
    ATOM_2_5,
    ATOM_ABOVE_MIN,
    ATOM_CET1,
    ATOM_GSIB,
    ATOM_LOSS,
    ATOM_RECAP,
    ATOM_RELEASE,
    ATOM_RESOLUTION,
    CCOB_KIND,
    CCYB_KIND,
    TLAC_KIND,
    verify_proof,
)


def claim(kind, text):
    return {
        "claim_id": "c1",
        "kind": kind,
        "start": 0,
        "end": len(text),
    }


class Tests(unittest.TestCase):
    def test_ccob_structure_context_proves_only_structural_facts(self):
        text = (
            "a 2.5% buffer comprised of Common Equity Tier 1 (CET1) "
            "above the regulatory minimum capital requirement"
        )
        out = verify_proof(
            text,
            source_id="doc:A",
            claims=[claim(CCOB_KIND, text)],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED", out)
        self.assertEqual(
            {x["id"] for x in out["proved_constraints"]},
            {ATOM_2_5, ATOM_CET1, ATOM_ABOVE_MIN},
        )
        self.assertFalse(out["concept_identity_claimed"])

    def test_ccob_context_without_above_minimum_is_rejected(self):
        text = "a 2.5% CET1 buffer"
        out = verify_proof(
            text,
            source_id="doc:A",
            claims=[claim(CCOB_KIND, text)],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"], [])

    def test_ccyb_release_context_proves_release_fact(self):
        text = "the cushion is released when system-wide risk crystallises or dissipates"
        out = verify_proof(
            text,
            source_id="doc:B",
            claims=[claim(CCYB_KIND, text)],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED", out)
        self.assertEqual(
            out["proved_constraints"],
            [{"op": "ATOM", "id": ATOM_RELEASE}],
        )
        self.assertFalse(out["concept_identity_claimed"])

    def test_ccyb_release_dissipates_only_is_accepted(self):
        text = "this buffer is released when system wide risk dissipates"
        out = verify_proof(
            text,
            source_id="doc:B",
            claims=[claim(CCYB_KIND, text)],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED", out)
        self.assertEqual(out["proved_constraints"][0]["id"], ATOM_RELEASE)

    def test_release_without_system_wide_risk_is_rejected(self):
        text = "the cushion is released when conditions improve"
        out = verify_proof(
            text,
            source_id="doc:B",
            claims=[claim(CCYB_KIND, text)],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"], [])

    def test_tlac_context_proves_loss_recap_and_resolution(self):
        text = (
            "sufficient loss-absorbing and recapitalisation capacity "
            "available in resolution"
        )
        out = verify_proof(
            text,
            source_id="doc:C",
            claims=[claim(TLAC_KIND, text)],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED", out)
        self.assertEqual(
            {x["id"] for x in out["proved_constraints"]},
            {ATOM_LOSS, ATOM_RECAP, ATOM_RESOLUTION},
        )
        self.assertNotIn(ATOM_GSIB, {x["id"] for x in out["proved_constraints"]})

    def test_tlac_context_adds_gsib_only_when_explicit(self):
        text = (
            "a failing G-SIB has sufficient loss-absorbing and "
            "recapitalization capacity available in resolution"
        )
        out = verify_proof(
            text,
            source_id="doc:C",
            claims=[claim(TLAC_KIND, text)],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED", out)
        self.assertIn(ATOM_GSIB, {x["id"] for x in out["proved_constraints"]})

    def test_resolution_without_recapitalisation_is_rejected(self):
        text = "loss-absorbing capacity available in resolution"
        out = verify_proof(
            text,
            source_id="doc:C",
            claims=[claim(TLAC_KIND, text)],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"], [])

    def test_wrong_claim_kind_does_not_cross_parse(self):
        text = (
            "sufficient loss-absorbing and recapitalisation capacity "
            "available in resolution"
        )
        out = verify_proof(
            text,
            source_id="doc:C",
            claims=[claim(CCYB_KIND, text)],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"], [])

    def test_exact_source_span_is_load_bearing(self):
        text = (
            "prefix. sufficient loss-absorbing and recapitalisation capacity "
            "available in resolution. suffix"
        )
        start = text.index("sufficient")
        end = text.index(". suffix")
        out = verify_proof(
            text,
            source_id="doc:C",
            claims=[{
                "claim_id": "c1",
                "kind": TLAC_KIND,
                "start": start,
                "end": end,
            }],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED", out)
        self.assertEqual(out["accepted_claims"][0]["source_span"], [start, end])

    def test_unmodeled_claim_field_is_rejected(self):
        text = "the cushion is released when system-wide risk dissipates"
        row = claim(CCYB_KIND, text)
        row["guessed_concept"] = "CCYB"
        out = verify_proof(text, source_id="doc:B", claims=[row])
        self.assertEqual(out["status"], "PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"], [])

    def test_duplicate_claim_id_fails_closed(self):
        text = "the cushion is released when system-wide risk dissipates"
        row = claim(CCYB_KIND, text)
        out = verify_proof(text, source_id="doc:B", claims=[row, dict(row)])
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_no_concept_identity_or_terminal_authority(self):
        text = "the cushion is released when system-wide risk dissipates"
        out = verify_proof(
            text,
            source_id="doc:B",
            claims=[claim(CCYB_KIND, text)],
        )
        self.assertTrue(out["semantic_truth_authority"])
        self.assertFalse(out["concept_identity_claimed"])
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
