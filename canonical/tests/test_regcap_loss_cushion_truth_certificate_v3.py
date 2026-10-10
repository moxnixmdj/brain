from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import regcap_loss_cushion_truth_certificate_v3 as cert
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel

TEXT = "loss-absorbing cushion"


def payload(claim_kind, target):
    return {
        "truth_kind": cert.TRUTH_KIND,
        "predicate_id": "caller-label",
        "claim_kind": claim_kind,
        "source_text": TEXT,
        "source_id": "doc:test",
        "start": 0,
        "end": len(TEXT),
        "target_concept_id": target,
    }


def selected(selected):
    return {
        "pass": True,
        "status": "OPEN__UNIQUE_REGCAP_SELECTION_RELATIVE_TO_FOUR_CONCEPT_BOUND_INVENTORY",
        "relative_selection_authority": True,
        "relative_selected_concept_id": selected,
        "candidate_concept_ids": [regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL],
        "semantic_identity_authority": False,
        "mapped_concept_id": None,
    }


class RegcapLossCushionTruthCertificateV3Tests(unittest.TestCase):
    def test_reproved_mrel_relative_selection_is_true_and_other_bound_member_false(self):
        with patch.object(cert.grounding, "ground", return_value=selected(mrel.MREL)):
            yes = cert.evaluate(payload("RELATIVE_RIVAL_SELECTION", mrel.MREL))
            no = cert.evaluate(payload("RELATIVE_RIVAL_SELECTION", regcap.TLAC))
        self.assertTrue(yes["pass"], yes)
        self.assertEqual(yes["predicate_truth"], "TRUE")
        self.assertTrue(yes["relative_selection_authority"])
        self.assertFalse(yes["semantic_identity_authority"])
        self.assertTrue(no["pass"], no)
        self.assertEqual(no["predicate_truth"], "FALSE")
        self.assertFalse(no["global_identity_authority"])

    def test_reproved_tlac_relative_selection_is_true(self):
        with patch.object(cert.grounding, "ground", return_value=selected(regcap.TLAC)):
            out = cert.evaluate(payload("RELATIVE_RIVAL_SELECTION", regcap.TLAC))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertTrue(out["semantic_truth_authority"])

    def test_unreproved_selection_remains_unknown(self):
        grounding = selected(regcap.TLAC)
        grounding["relative_selection_authority"] = False
        grounding["relative_selected_concept_id"] = None
        with patch.object(cert.grounding, "ground", return_value=grounding):
            out = cert.evaluate(payload("RELATIVE_RIVAL_SELECTION", regcap.TLAC))
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertEqual(out["reason"], "UNIQUE_BOUND_RIVAL_SELECTION_NOT_PROVED")

    def test_predicate_identity_changes_with_v5_grounding_schema(self):
        pid = cert.checked_predicate_id(
            source_id="doc:test",
            source_text=TEXT,
            start=0,
            end=len(TEXT),
            claim_kind="RELATIVE_RIVAL_SELECTION",
            target_concept_id=regcap.TLAC,
        )
        self.assertTrue(pid.startswith("regcap-loss-cushion-sha256:"))
        self.assertEqual(cert.grounding.SCHEMA, "PROJECT_BRAIN_LOSS_ABSORBING_CUSHION_REGCAP_GROUNDING_V5")

    def test_source_local_identity_remains_preserved(self):
        grounding = {
            "pass": True,
            "status": "PASS__SOURCE_BOUND_LOSS_ABSORBING_CUSHION_MAPPED_TO_CCOB",
            "semantic_identity_authority": True,
            "mapped_concept_id": regcap.CCOB,
            "candidate_concept_ids": [regcap.CCOB],
        }
        with patch.object(cert.grounding, "ground", return_value=grounding):
            out = cert.evaluate(payload("SOURCE_LOCAL_IDENTITY", regcap.CCOB))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertTrue(out["semantic_identity_authority"])
        self.assertFalse(out["global_identity_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
