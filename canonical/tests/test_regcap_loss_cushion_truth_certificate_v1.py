import unittest
from unittest.mock import patch

from canonical.runtime.regcap_loss_cushion_truth_certificate_v1 import (
    checked_predicate_id,
    evaluate,
)

RAW = "loss-absorbing cushion"


def relative_result(selected="REGCAP::CCYB"):
    return {
        "status": "OPEN__UNIQUE_REGCAP_SELECTION_RELATIVE_TO_BOUND_RIVALS",
        "pass": True,
        "candidate_concept_ids": ["REGCAP::CCOB", "REGCAP::CCYB", "REGCAP::TLAC"],
        "relative_selection_authority": True,
        "relative_selected_concept_id": selected,
        "mapped_concept_id": None,
        "semantic_identity_authority": False,
        "terminal_authority": False,
    }


def identity_result():
    return {
        "status": "PASS__SOURCE_BOUND_LOSS_ABSORBING_CUSHION_MAPPED_TO_CCOB",
        "pass": True,
        "candidate_concept_ids": ["REGCAP::CCOB"],
        "relative_selection_authority": False,
        "relative_selected_concept_id": None,
        "mapped_concept_id": "REGCAP::CCOB",
        "semantic_identity_authority": True,
        "terminal_authority": False,
    }


class Tests(unittest.TestCase):
    def payload(self, claim, target):
        return {
            "truth_kind": "REGCAP_LOSS_CUSHION_GROUNDING",
            "predicate_id": "caller-label",
            "claim_kind": claim,
            "source_text": RAW,
            "source_id": "doc:A",
            "start": 0,
            "end": len(RAW),
            "target_concept_id": target,
        }

    def test_relative_selection_true_is_authoritative_but_not_identity(self):
        with patch(
            "canonical.runtime.regcap_loss_cushion_truth_certificate_v1.grounding.ground",
            return_value=relative_result(),
        ):
            out = evaluate(self.payload("RELATIVE_RIVAL_SELECTION", "REGCAP::CCYB"))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertTrue(out["truthful_precommitment_observation"])
        self.assertTrue(out["semantic_truth_authority"])
        self.assertTrue(out["relative_selection_authority"])
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["global_identity_authority"])
        self.assertFalse(out["candidate_universe_complete"])
        self.assertFalse(out["terminal_authority"])

    def test_relative_selection_can_prove_false_for_another_bound_rival(self):
        with patch(
            "canonical.runtime.regcap_loss_cushion_truth_certificate_v1.grounding.ground",
            return_value=relative_result(),
        ):
            out = evaluate(self.payload("RELATIVE_RIVAL_SELECTION", "REGCAP::CCOB"))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "FALSE")
        self.assertFalse(out["semantic_identity_authority"])

    def test_relative_selection_target_outside_bound_rivals_is_unknown(self):
        with patch(
            "canonical.runtime.regcap_loss_cushion_truth_certificate_v1.grounding.ground",
            return_value=relative_result(),
        ):
            out = evaluate(self.payload("RELATIVE_RIVAL_SELECTION", "REGCAP::MREL"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertFalse(out["truthful_precommitment_observation"])

    def test_absent_relative_selection_is_unknown(self):
        unresolved = {
            **relative_result(),
            "relative_selection_authority": False,
            "relative_selected_concept_id": None,
        }
        with patch(
            "canonical.runtime.regcap_loss_cushion_truth_certificate_v1.grounding.ground",
            return_value=unresolved,
        ):
            out = evaluate(self.payload("RELATIVE_RIVAL_SELECTION", "REGCAP::CCYB"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"], "UNKNOWN")

    def test_source_local_identity_true_requires_stronger_identity_path(self):
        with patch(
            "canonical.runtime.regcap_loss_cushion_truth_certificate_v1.grounding.ground",
            return_value=identity_result(),
        ):
            out = evaluate(self.payload("SOURCE_LOCAL_IDENTITY", "REGCAP::CCOB"))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertTrue(out["semantic_identity_authority"])
        self.assertFalse(out["global_identity_authority"])

    def test_different_local_identity_does_not_mint_negative_identity(self):
        with patch(
            "canonical.runtime.regcap_loss_cushion_truth_certificate_v1.grounding.ground",
            return_value=identity_result(),
        ):
            out = evaluate(self.payload("SOURCE_LOCAL_IDENTITY", "REGCAP::TLAC"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"], "UNKNOWN")

    def test_checked_id_ignores_caller_predicate_label(self):
        expected = checked_predicate_id(
            source_id="doc:A",
            source_text=RAW,
            start=0,
            end=len(RAW),
            claim_kind="RELATIVE_RIVAL_SELECTION",
            target_concept_id="REGCAP::CCYB",
        )
        with patch(
            "canonical.runtime.regcap_loss_cushion_truth_certificate_v1.grounding.ground",
            return_value=relative_result(),
        ):
            out = evaluate(self.payload("RELATIVE_RIVAL_SELECTION", "REGCAP::CCYB"))
        self.assertEqual(out["predicate_id"], expected)
        self.assertEqual(out["requested_predicate_id"], "caller-label")
        self.assertFalse(out["requested_predicate_id_authority"])

    def test_grounding_fail_closed_propagates(self):
        with patch(
            "canonical.runtime.regcap_loss_cushion_truth_certificate_v1.grounding.ground",
            return_value={"status": "FAIL_CLOSED", "pass": False, "reason": "x"},
        ):
            out = evaluate(self.payload("RELATIVE_RIVAL_SELECTION", "REGCAP::CCYB"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["predicate_truth"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
