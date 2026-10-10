from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import semantic_truth_dispatch_v1 as dispatch
from canonical.runtime import regcap_loss_cushion_truth_certificate_v5 as cert5


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
        with patch.object(cert5.grounding, "ground", return_value=v7_result):
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
        self.assertEqual(out["grounding_result"]["schema"] if "schema" in out["grounding_result"] else cert5.grounding.SCHEMA, cert5.grounding.SCHEMA)

    def test_dispatch_routes_loss_cushion_truth_to_v5(self):
        expected = {
            "pass": True,
            "status": "PASS__V5_SENTINEL",
            "predicate_truth": "TRUE",
        }
        with patch(
            "canonical.runtime.regcap_loss_cushion_truth_certificate_v5.evaluate",
            return_value=expected,
        ) as routed:
            out = dispatch.evaluate({
                "truth_kind": "REGCAP_LOSS_CUSHION_GROUNDING",
                "predicate_id": "x",
            })
        self.assertEqual(out, expected)
        routed.assert_called_once()

    def test_v4_remains_historical_not_live_dispatch_target(self):
        with patch(
            "canonical.runtime.regcap_loss_cushion_truth_certificate_v5.evaluate",
            return_value={"pass": True, "status": "V5", "predicate_truth": "TRUE"},
        ) as v5, patch(
            "canonical.runtime.regcap_loss_cushion_truth_certificate_v4.evaluate",
            side_effect=AssertionError("historical V4 must not be dispatched"),
        ):
            out = dispatch.evaluate({
                "truth_kind": "REGCAP_LOSS_CUSHION_GROUNDING",
                "predicate_id": "x",
            })
        self.assertEqual(out["status"], "V5")
        v5.assert_called_once()

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
