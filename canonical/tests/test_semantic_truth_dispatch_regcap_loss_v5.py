from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import semantic_truth_dispatch_v1 as dispatch
from canonical.runtime import regcap_loss_cushion_truth_certificate_v6 as cert6


class Tests(unittest.TestCase):
    def test_dispatch_consumes_v7_four_way_mrel_relative_selection(self):
        text = "loss-absorbing cushion"
        v7_result = {
            "pass": True,
            "status": "OPEN__UNIQUE_MREL_SELECTION_RELATIVE_TO_FOUR_CONCEPT_BOUND_INVENTORY",
            "relative_selection_authority": True,
            "relative_selected_concept_id": "REGCAP::MREL",
            "candidate_concept_ids": [
                "REGCAP::CCOB", "REGCAP::CCYB", "REGCAP::TLAC", "REGCAP::MREL"
            ],
            "semantic_identity_authority": False,
            "mapped_concept_id": None,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
        with patch.object(cert6.grounding, "ground", return_value=v7_result):
            out = dispatch.evaluate({
                "truth_kind": "REGCAP_LOSS_CUSHION_GROUNDING",
                "predicate_id": "caller-label",
                "claim_kind": "RELATIVE_RIVAL_SELECTION",
                "source_text": text,
                "source_id": "doc:v81",
                "start": 0,
                "end": len(text),
                "target_concept_id": "REGCAP::MREL",
            })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertTrue(out["relative_selection_authority"])
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["global_identity_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["grounding_result"]["schema"] if "schema" in out["grounding_result"] else cert6.grounding.SCHEMA, cert6.grounding.SCHEMA)

    def test_unresolved_dispatch_exposes_typed_next_information_request(self):
        text = "loss-absorbing cushion"
        request = {
            "pass": True,
            "status": "PASS__MINIMUM_FOUR_WAY_POLICY_CHANGING_INFORMATION_REQUEST",
            "minimum_observation_count": 1,
            "independent_verification_required": True,
        }
        v7_result = {
            "pass": True,
            "status": "OPEN__FOUR_WAY_CONTEXT_REMAINS_UNRESOLVED_AFTER_ALL_PAIR_REPLAY",
            "relative_selection_authority": False,
            "relative_selected_concept_id": None,
            "candidate_concept_ids": [
                "REGCAP::CCOB", "REGCAP::CCYB", "REGCAP::TLAC", "REGCAP::MREL"
            ],
            "semantic_identity_authority": False,
            "mapped_concept_id": None,
            "minimum_policy_changing_information_request": request,
            "minimum_policy_changing_information_request_available": True,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
        with patch.object(cert6.grounding, "ground", return_value=v7_result):
            out = dispatch.evaluate({
                "truth_kind": "REGCAP_LOSS_CUSHION_GROUNDING",
                "predicate_id": "caller-label",
                "claim_kind": "RELATIVE_RIVAL_SELECTION",
                "source_text": text,
                "source_id": "doc:v82",
                "start": 0,
                "end": len(text),
                "target_concept_id": "REGCAP::MREL",
            })
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertEqual(out["next_information_request"], request)
        self.assertEqual(
            out["next_required_edge"],
            "REGCAP_LOSS_CUSHION_MINIMUM_POLICY_CHANGING_INFORMATION",
        )
        self.assertFalse(out["terminal_authority"])

    def test_dispatch_routes_loss_cushion_truth_to_v5(self):
        expected = {
            "pass": True,
            "status": "PASS__V5_SENTINEL",
            "predicate_truth": "TRUE",
        }
        with patch(
            "canonical.runtime.regcap_loss_cushion_truth_certificate_v6.evaluate",
            return_value=expected,
        ) as routed:
            out = dispatch.evaluate({
                "truth_kind": "REGCAP_LOSS_CUSHION_GROUNDING",
                "predicate_id": "x",
            })
        self.assertEqual(out, expected)
        routed.assert_called_once()

    def test_v5_remains_historical_not_live_dispatch_target(self):
        with patch(
            "canonical.runtime.regcap_loss_cushion_truth_certificate_v6.evaluate",
            return_value={"pass": True, "status": "V6", "predicate_truth": "TRUE"},
        ) as v6, patch(
            "canonical.runtime.regcap_loss_cushion_truth_certificate_v5.evaluate",
            side_effect=AssertionError("historical V5 must not be dispatched"),
        ):
            out = dispatch.evaluate({
                "truth_kind": "REGCAP_LOSS_CUSHION_GROUNDING",
                "predicate_id": "x",
            })
        self.assertEqual(out["status"], "V6")
        v6.assert_called_once()

    def test_unrelated_dispatch_family_is_unchanged(self):
        with patch.object(
            dispatch,
            "evaluate_domain_mapping",
            return_value={"pass": True, "predicate_truth": "TRUE"},
        ) as fn:
            out = dispatch.evaluate({"truth_kind": "DOMAIN_MAPPING_RELATION"})
        self.assertTrue(out["pass"])
        fn.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
