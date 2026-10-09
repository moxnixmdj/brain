from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import regcap_loss_cushion_truth_certificate_v2 as cert
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap


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


class Tests(unittest.TestCase):
    def test_invalidated_legacy_relative_selection_is_unknown(self):
        grounding = {
            "pass": True,
            "status": "OPEN__LEGACY_THREE_RIVAL_SELECTION_INVALIDATED_BY_EXPANDED_BOUND_INVENTORY",
            "relative_selection_authority": False,
            "relative_selected_concept_id": None,
            "candidate_concept_ids": [
                regcap.CCOB,
                regcap.CCYB,
                regcap.TLAC,
                "REGCAP::MREL",
            ],
            "semantic_identity_authority": False,
        }
        with patch.object(cert.grounding, "ground", return_value=grounding):
            out = cert.evaluate(payload("RELATIVE_RIVAL_SELECTION", regcap.TLAC))
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertEqual(out["reason"], "UNIQUE_BOUND_RIVAL_SELECTION_NOT_PROVED")
        self.assertFalse(out["semantic_truth_authority"])

    def test_source_local_identity_is_preserved(self):
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
        self.assertFalse(out["terminal_authority"])

    def test_different_source_local_identity_does_not_prove_negation(self):
        grounding = {
            "pass": True,
            "status": "PASS__SOURCE_BOUND_LOSS_ABSORBING_CUSHION_MAPPED_TO_CCOB",
            "semantic_identity_authority": True,
            "mapped_concept_id": regcap.CCOB,
            "candidate_concept_ids": [regcap.CCOB],
        }
        with patch.object(cert.grounding, "ground", return_value=grounding):
            out = cert.evaluate(payload("SOURCE_LOCAL_IDENTITY", regcap.TLAC))
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertEqual(
            out["reason"],
            "DIFFERENT_SOURCE_LOCAL_IDENTITY_DOES_NOT_BY_ITSELF_PROVE_NEGATION",
        )

    def test_grounding_failure_fails_closed(self):
        with patch.object(
            cert.grounding,
            "ground",
            return_value={"pass": False, "status": "FAIL_CLOSED", "reason": "forced"},
        ):
            out = cert.evaluate(payload("RELATIVE_RIVAL_SELECTION", regcap.TLAC))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["predicate_truth"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
