from __future__ import annotations

import unittest

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v4 as grounding
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import regcap_loss_cushion_truth_certificate_v2 as cert
from canonical.runtime import semantic_truth_dispatch_v1 as dispatch

TEXT = "loss-absorbing cushion"
SOURCE_ID = "doc:generic-loss-cushion"


class CurrentMainMrelExpandedLossCushionTests(unittest.TestCase):
    def test_real_grounding_frontier_includes_mrel_and_revokes_three_rival_selection(self):
        out = grounding.ground(
            TEXT,
            source_id=SOURCE_ID,
            start=0,
            end=len(TEXT),
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["candidate_concept_ids"],
            sorted([regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL]),
        )
        self.assertIn(mrel.MREL, out["expanded_candidate_ids_added"])
        self.assertFalse(out["relative_selection_authority"])
        self.assertIsNone(out["relative_selected_concept_id"])
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["open_world_candidate_set_complete"])
        self.assertTrue(out["opaque_remainder_required"])

    def test_real_truth_certificate_does_not_reuse_stale_tlac_selection(self):
        predicate_id = cert.checked_predicate_id(
            source_id=SOURCE_ID,
            source_text=TEXT,
            start=0,
            end=len(TEXT),
            claim_kind="RELATIVE_RIVAL_SELECTION",
            target_concept_id=regcap.TLAC,
        )
        out = cert.evaluate(
            {
                "truth_kind": cert.TRUTH_KIND,
                "predicate_id": predicate_id,
                "claim_kind": "RELATIVE_RIVAL_SELECTION",
                "source_text": TEXT,
                "source_id": SOURCE_ID,
                "start": 0,
                "end": len(TEXT),
                "target_concept_id": regcap.TLAC,
            }
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertEqual(
            out["reason"],
            "UNIQUE_BOUND_RIVAL_SELECTION_NOT_PROVED",
        )
        self.assertIn(mrel.MREL, out["grounding_result"]["candidate_concept_ids"])

    def test_dispatch_uses_mrel_aware_certificate_on_real_payload(self):
        predicate_id = cert.checked_predicate_id(
            source_id=SOURCE_ID,
            source_text=TEXT,
            start=0,
            end=len(TEXT),
            claim_kind="RELATIVE_RIVAL_SELECTION",
            target_concept_id=regcap.TLAC,
        )
        out = dispatch.evaluate(
            {
                "truth_kind": "REGCAP_LOSS_CUSHION_GROUNDING",
                "predicate_id": predicate_id,
                "claim_kind": "RELATIVE_RIVAL_SELECTION",
                "source_text": TEXT,
                "source_id": SOURCE_ID,
                "start": 0,
                "end": len(TEXT),
                "target_concept_id": regcap.TLAC,
            }
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertIn(mrel.MREL, out["grounding_result"]["candidate_concept_ids"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
