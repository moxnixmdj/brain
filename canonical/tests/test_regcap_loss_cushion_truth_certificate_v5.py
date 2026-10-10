from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import regcap_loss_cushion_truth_certificate_v5 as cert
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel

TEXT = "loss-absorbing cushion"


def payload(target, claim_kind="RELATIVE_RIVAL_SELECTION"):
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
    def test_predicate_identity_is_bound_to_v7_grounding_schema(self):
        pid = cert.checked_predicate_id(source_id="doc:test", source_text=TEXT, start=0, end=len(TEXT), claim_kind="RELATIVE_RIVAL_SELECTION", target_concept_id=mrel.MREL)
        self.assertTrue(pid.startswith("regcap-loss-cushion-sha256:"))
        self.assertEqual(cert.grounding.SCHEMA, "PROJECT_BRAIN_LOSS_ABSORBING_CUSHION_REGCAP_GROUNDING_V7")

    def test_four_rival_selection_proves_true_for_selected_target(self):
        grounding = {
            "pass": True,
            "status": "OPEN__UNIQUE_REGCAP_SELECTION_RELATIVE_TO_FOUR_CONCEPT_BOUND_INVENTORY",
            "relative_selection_authority": True,
            "relative_selected_concept_id": regcap.CCOB,
            "candidate_concept_ids": [
                regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL,
            ],
            "semantic_identity_authority": False,
        }
        with patch.object(cert.grounding, "ground", return_value=grounding):
            out = cert.evaluate(payload(regcap.CCOB))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertTrue(out["relative_selection_authority"])
        self.assertFalse(out["semantic_identity_authority"])

    def test_four_rival_selection_proves_false_for_other_bound_target(self):
        grounding = {
            "pass": True,
            "status": "OPEN__UNIQUE_REGCAP_SELECTION_RELATIVE_TO_FOUR_CONCEPT_BOUND_INVENTORY",
            "relative_selection_authority": True,
            "relative_selected_concept_id": regcap.CCYB,
            "candidate_concept_ids": [
                regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL,
            ],
            "semantic_identity_authority": False,
        }
        with patch.object(cert.grounding, "ground", return_value=grounding):
            out = cert.evaluate(payload(mrel.MREL))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "FALSE")
        self.assertFalse(out["global_identity_authority"])

    def test_unresolved_pair_stays_unknown(self):
        request = {
            "pass": True,
            "status": "PASS__MINIMUM_FOUR_WAY_POLICY_CHANGING_INFORMATION_REQUEST",
            "minimum_observation_count": 1,
            "independent_verification_required": True,
        }
        grounding = {
            "pass": True,
            "status": "OPEN__ANCHOR_MREL_PAIR_REMAINS_UNRESOLVED",
            "relative_selection_authority": False,
            "relative_selected_concept_id": None,
            "candidate_concept_ids": [
                regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL,
            ],
            "semantic_identity_authority": False,
            "minimum_policy_changing_information_request": request,
            "minimum_policy_changing_information_request_available": True,
        }
        with patch.object(cert.grounding, "ground", return_value=grounding):
            out = cert.evaluate(payload(regcap.CCOB))
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertFalse(out["semantic_truth_authority"])
        self.assertEqual(out["next_information_request"], request)
        self.assertEqual(
            out["next_required_edge"],
            "REGCAP_LOSS_CUSHION_MINIMUM_POLICY_CHANGING_INFORMATION",
        )
        self.assertEqual(out["next_information_request_source"], cert.grounding.SCHEMA)
        template = out["checker_materialization_template"]
        self.assertEqual(
            template["schema"],
            "PROJECT_BRAIN_SEMANTIC_TRUTH_MATERIALIZATION_TEMPLATE_V1",
        )
        self.assertEqual(template["truth_kind"], cert.TRUTH_KIND)
        self.assertEqual(template["claim_kind"], "RELATIVE_RIVAL_SELECTION")
        self.assertEqual(template["target_concept_id"], regcap.CCOB)
        self.assertEqual(
            template["required_evidence_fields"],
            ["source_text", "source_id", "start", "end"],
        )
        self.assertTrue(template["source_span_must_be_rederived"])
        self.assertTrue(
            template["replacement_source_does_not_inherit_original_predicate_identity"]
        )
        self.assertFalse(template["requested_predicate_id_authority"])
        self.assertFalse(template["provider_semantic_truth_authority"])
        self.assertNotIn("source_text", template)
        self.assertNotIn("source_id", template)
        self.assertNotIn("start", template)
        self.assertNotIn("end", template)
        self.assertFalse(out["terminal_authority"])

    def test_source_local_identity_remains_true_only_for_mapped_target(self):
        grounding = {
            "pass": True,
            "status": "PASS__SOURCE_LOCAL_IDENTITY",
            "semantic_identity_authority": True,
            "mapped_concept_id": regcap.CCOB,
            "candidate_concept_ids": [regcap.CCOB],
        }
        with patch.object(cert.grounding, "ground", return_value=grounding):
            out = cert.evaluate(payload(regcap.CCOB, "SOURCE_LOCAL_IDENTITY"))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertTrue(out["semantic_identity_authority"])
        self.assertFalse(out["global_identity_authority"])

    def test_no_terminal_authority(self):
        grounding = {
            "pass": True,
            "status": "OPEN__UNIQUE_REGCAP_SELECTION_RELATIVE_TO_FOUR_CONCEPT_BOUND_INVENTORY",
            "relative_selection_authority": True,
            "relative_selected_concept_id": mrel.MREL,
            "candidate_concept_ids": [
                regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL,
            ],
            "semantic_identity_authority": False,
        }
        with patch.object(cert.grounding, "ground", return_value=grounding):
            out = cert.evaluate(payload(mrel.MREL))
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
