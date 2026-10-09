from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v4 as v4
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel


class Tests(unittest.TestCase):
    def test_exact_source_identity_is_preserved_without_weaker_expansion(self):
        base = {
            "pass": True,
            "status": "PASS__SOURCE_BOUND_LOSS_ABSORBING_CUSHION_MAPPED_TO_CCOB",
            "semantic_identity_authority": True,
            "mapped_concept_id": regcap.CCOB,
            "candidate_concept_ids": [regcap.CCOB],
        }
        with patch.object(v4.v3, "ground", return_value=base), patch.object(
            v4.discovery, "discover"
        ) as discover:
            out = v4.ground("loss-absorbing cushion", source_id="s", start=0, end=22)
        self.assertTrue(out["semantic_identity_authority"])
        self.assertEqual(out["mapped_concept_id"], regcap.CCOB)
        self.assertFalse(out["expanded_candidate_discovery_attempted"])
        discover.assert_not_called()

    def test_expanded_frontier_adds_mrel_and_invalidates_old_unique_tlac(self):
        base = {
            "pass": True,
            "status": "OPEN__UNIQUE_REGCAP_SELECTION_RELATIVE_TO_BOUND_RIVALS",
            "source_constraint_proved": True,
            "candidate_concept_ids": [regcap.CCOB, regcap.CCYB, regcap.TLAC],
            "candidate_generation_authority": True,
            "relative_selection_authority": True,
            "relative_selected_concept_id": regcap.TLAC,
            "bound_rival_surviving_concept_ids": [regcap.TLAC],
            "mapped_concept_id": None,
            "semantic_identity_authority": False,
        }
        expanded = {
            "pass": True,
            "status": "OPEN__NON_UNIQUE_PROPERTY_CANDIDATES",
            "candidate_generation_authority": True,
            "candidate_set_complete_relative_to_bound_inventory": True,
            "candidate_concept_ids": [regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL],
            "candidates": [],
        }
        with patch.object(v4.v3, "ground", return_value=base), patch.object(
            v4.discovery, "discover", return_value=expanded
        ):
            out = v4.ground("loss-absorbing cushion", source_id="s", start=0, end=22)

        self.assertIn(mrel.MREL, out["candidate_concept_ids"])
        self.assertFalse(out["relative_selection_authority"])
        self.assertIsNone(out["relative_selected_concept_id"])
        self.assertEqual(out["legacy_v3_relative_selected_concept_id"], regcap.TLAC)
        self.assertEqual(
            out["status"],
            "OPEN__LEGACY_THREE_RIVAL_SELECTION_INVALIDATED_BY_EXPANDED_BOUND_INVENTORY",
        )

    def test_expanded_candidate_authority_failure_fails_closed_not_stale(self):
        base = {
            "pass": True,
            "status": "OPEN__COMPOSED_SOURCE_MEANING_WITH_NON_UNIQUE_REGCAP_CANDIDATES",
            "source_constraint_proved": True,
            "candidate_concept_ids": [regcap.CCOB, regcap.CCYB, regcap.TLAC],
            "candidate_generation_authority": True,
            "semantic_identity_authority": False,
        }
        failed = {"pass": False, "status": "FAIL_CLOSED", "reason": "MREL_SOURCE_DRIFT"}
        with patch.object(v4.v3, "ground", return_value=base), patch.object(
            v4.discovery, "discover", return_value=failed
        ):
            out = v4.ground("loss-absorbing cushion", source_id="s", start=0, end=22)

        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["candidate_concept_ids"], [])
        self.assertFalse(out["candidate_generation_authority"])
        self.assertFalse(out["relative_selection_authority"])

    def test_nonidentity_frontier_stays_open_world(self):
        base = {
            "pass": True,
            "status": "OPEN__COMPOSED_SOURCE_MEANING_WITH_NON_UNIQUE_REGCAP_CANDIDATES",
            "source_constraint_proved": True,
            "candidate_concept_ids": [regcap.CCOB, regcap.CCYB, regcap.TLAC],
            "candidate_generation_authority": True,
            "relative_selection_authority": False,
            "semantic_identity_authority": False,
        }
        expanded = {
            "pass": True,
            "status": "OPEN__NON_UNIQUE_PROPERTY_CANDIDATES",
            "candidate_generation_authority": True,
            "candidate_set_complete_relative_to_bound_inventory": True,
            "candidate_concept_ids": [regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL],
            "candidates": [],
        }
        with patch.object(v4.v3, "ground", return_value=base), patch.object(
            v4.discovery, "discover", return_value=expanded
        ):
            out = v4.ground("loss-absorbing cushion", source_id="s", start=0, end=22)

        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["open_world_candidate_set_complete"])
        self.assertTrue(out["opaque_remainder_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
