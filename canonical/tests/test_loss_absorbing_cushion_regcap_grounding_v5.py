from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v5 as v5
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel


def eligible_base(selected=regcap.TLAC):
    return {
        "schema": "PROJECT_BRAIN_LOSS_ABSORBING_CUSHION_REGCAP_GROUNDING_V4",
        "status": "OPEN__LEGACY_THREE_RIVAL_SELECTION_INVALIDATED_BY_EXPANDED_BOUND_INVENTORY",
        "pass": True,
        "source_constraint_proved": True,
        "candidate_concept_ids": sorted([regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL]),
        "candidate_set_complete_relative_to_bound_inventory": True,
        "expanded_candidate_ids_added": [mrel.MREL],
        "legacy_v3_relative_selection_authority": True,
        "legacy_v3_relative_selected_concept_id": selected,
        "legacy_v3_bound_rival_surviving_concept_ids": [selected],
        "context_signature_result": {"semantic_truth_authority": True},
        "relative_selection_authority": False,
        "relative_selected_concept_id": None,
        "semantic_identity_authority": False,
        "mapped_concept_id": None,
        "opaque_remainder_required": True,
    }


def pair_result(selected):
    return {
        "schema": "PROJECT_BRAIN_TLAC_MREL_IDENTITY_DISCRIMINATOR_V1",
        "status": "PASS__UNIQUE_TLAC_MREL_CONCEPT_IN_BOUND_PAIR_SCOPE",
        "pass": True,
        "semantic_truth_authority": True,
        "relative_selection_authority": True,
        "candidate_universe_complete": True,
        "selected_concept_id": selected,
        "surviving_candidate_ids": [selected],
    }


class LossAbsorbingCushionRegcapGroundingV5Tests(unittest.TestCase):
    def test_composes_legacy_tlac_survivor_with_pair_tlac_to_reprove_relative_selection(self):
        with patch.object(v5.v4, "ground", return_value=eligible_base()), patch.object(
            v5.pair, "resolve_relative", return_value=pair_result(regcap.TLAC)
        ) as resolver:
            out = v5.ground("x", source_id="s", start=0, end=1)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["relative_selection_authority"])
        self.assertEqual(out["relative_selected_concept_id"], regcap.TLAC)
        self.assertEqual(out["bound_rival_surviving_concept_ids"], [regcap.TLAC])
        self.assertTrue(out["four_concept_relative_selection_reproved"])
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["open_world_candidate_set_complete"])
        resolver.assert_called_once()

    def test_composes_legacy_tlac_survivor_with_pair_mrel(self):
        with patch.object(v5.v4, "ground", return_value=eligible_base()), patch.object(
            v5.pair, "resolve_relative", return_value=pair_result(mrel.MREL)
        ):
            out = v5.ground("x", source_id="s", start=0, end=1)
        self.assertTrue(out["relative_selection_authority"])
        self.assertEqual(out["relative_selected_concept_id"], mrel.MREL)
        self.assertEqual(out["bound_rival_surviving_concept_ids"], [mrel.MREL])
        self.assertFalse(out["semantic_identity_authority"])

    def test_no_pair_marker_preserves_safe_v4_open_state(self):
        open_pair = {
            "status": "OPEN__NO_BOUND_TLAC_MREL_IDENTITY_DISCRIMINATOR",
            "pass": False,
            "relative_selection_authority": False,
        }
        with patch.object(v5.v4, "ground", return_value=eligible_base()), patch.object(
            v5.pair, "resolve_relative", return_value=open_pair
        ):
            out = v5.ground("x", source_id="s", start=0, end=1)
        self.assertFalse(out["relative_selection_authority"])
        self.assertIsNone(out["relative_selected_concept_id"])
        self.assertEqual(
            out["pair_recomposition_reason"],
            "NO_AUTHENTICATED_TLAC_MREL_GOVERNING_REQUIREMENT_MARKER",
        )

    def test_pair_fail_closed_never_restores_legacy_selection(self):
        failed = {"status": "FAIL_CLOSED", "pass": False, "reason": "CONFLICT"}
        with patch.object(v5.v4, "ground", return_value=eligible_base()), patch.object(
            v5.pair, "resolve_relative", return_value=failed
        ):
            out = v5.ground("x", source_id="s", start=0, end=1)
        self.assertFalse(out["relative_selection_authority"])
        self.assertIsNone(out["relative_selected_concept_id"])
        self.assertTrue(out["pair_recomposition_preserved_safe_v4_open_state"])

    def test_non_tlac_legacy_selection_cannot_use_tlac_mrel_pair_discriminator(self):
        with patch.object(
            v5.v4, "ground", return_value=eligible_base(regcap.CCOB)
        ), patch.object(v5.pair, "resolve_relative") as resolver:
            out = v5.ground("x", source_id="s", start=0, end=1)
        self.assertFalse(out["relative_selection_authority"])
        self.assertFalse(out["pair_recomposition_attempted"])
        self.assertEqual(out["pair_recomposition_reason"], "LEGACY_SELECTION_NOT_TLAC")
        resolver.assert_not_called()

    def test_incomplete_four_concept_inventory_cannot_recompose(self):
        base = eligible_base()
        base["candidate_concept_ids"] = [regcap.TLAC, mrel.MREL]
        with patch.object(v5.v4, "ground", return_value=base), patch.object(
            v5.pair, "resolve_relative"
        ) as resolver:
            out = v5.ground("x", source_id="s", start=0, end=1)
        self.assertFalse(out["pair_recomposition_attempted"])
        self.assertEqual(
            out["pair_recomposition_reason"],
            "EXPANDED_FRONTIER_NOT_EXACT_FOUR_CONCEPT_INVENTORY",
        )
        resolver.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
