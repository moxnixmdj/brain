from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v6 as v6
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel


FOUR = [regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL]


def base_for(anchor):
    return {
        "pass": True,
        "status": "OPEN__LEGACY_THREE_RIVAL_SELECTION_INVALIDATED_BY_EXPANDED_BOUND_INVENTORY",
        "candidate_concept_ids": list(FOUR),
        "candidate_set_complete_relative_to_bound_inventory": True,
        "expanded_candidate_ids_added": [mrel.MREL],
        "legacy_v3_relative_selection_authority": True,
        "legacy_v3_relative_selected_concept_id": anchor,
        "legacy_v3_bound_rival_surviving_concept_ids": [anchor],
        "context_signature_result": {
            "semantic_truth_authority": True,
        },
        "relative_selection_authority": False,
        "relative_selected_concept_id": None,
        "semantic_identity_authority": False,
        "mapped_concept_id": None,
    }


def pair_selected(selected):
    return {
        "pass": True,
        "status": "PASS__UNIQUE_CONCEPT_IN_BOUND_REGCAP_MREL_PAIR_SCOPE",
        "relative_selection_authority": True,
        "selected_concept_id": selected,
    }


class Tests(unittest.TestCase):
    def test_ccob_pair_revalidation_restores_relative_selection(self):
        with patch.object(v6.v5, "ground", return_value=base_for(regcap.CCOB)):
            with patch.object(
                v6.pair,
                "resolve_relative",
                return_value=pair_selected(regcap.CCOB),
            ) as fn:
                out = v6.ground(
                    "loss-absorbing cushion",
                    source_id="doc:ccob",
                    start=0,
                    end=len("loss-absorbing cushion"),
                )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["relative_selection_authority"])
        self.assertEqual(out["relative_selected_concept_id"], regcap.CCOB)
        self.assertTrue(out["four_concept_relative_selection_reproved"])
        self.assertFalse(out["semantic_identity_authority"])
        fn.assert_called_once()
        self.assertEqual(fn.call_args.kwargs["pair_id"], v6.pair.CCOB_MREL)

    def test_ccyb_pair_revalidation_restores_relative_selection(self):
        with patch.object(v6.v5, "ground", return_value=base_for(regcap.CCYB)):
            with patch.object(
                v6.pair,
                "resolve_relative",
                return_value=pair_selected(regcap.CCYB),
            ) as fn:
                out = v6.ground(
                    "loss-absorbing cushion",
                    source_id="doc:ccyb",
                    start=0,
                    end=len("loss-absorbing cushion"),
                )
        self.assertTrue(out["relative_selection_authority"])
        self.assertEqual(out["relative_selected_concept_id"], regcap.CCYB)
        self.assertEqual(fn.call_args.kwargs["pair_id"], v6.pair.CCYB_MREL)

    def test_pair_can_in_principle_select_mrel_inside_exact_pair(self):
        with patch.object(v6.v5, "ground", return_value=base_for(regcap.CCOB)):
            with patch.object(
                v6.pair,
                "resolve_relative",
                return_value=pair_selected(mrel.MREL),
            ):
                out = v6.ground(
                    "loss-absorbing cushion",
                    source_id="doc:mrel",
                    start=0,
                    end=len("loss-absorbing cushion"),
                )
        self.assertTrue(out["relative_selection_authority"])
        self.assertEqual(out["relative_selected_concept_id"], mrel.MREL)

    def test_missing_pair_marker_keeps_anchor_and_mrel_open(self):
        unresolved = {
            "pass": False,
            "status": "OPEN__NO_BOUND_PAIR_CONTEXT_SIGNATURE",
            "relative_selection_authority": False,
        }
        with patch.object(v6.v5, "ground", return_value=base_for(regcap.CCOB)):
            with patch.object(v6.pair, "resolve_relative", return_value=unresolved):
                out = v6.ground(
                    "loss-absorbing cushion",
                    source_id="doc:open",
                    start=0,
                    end=len("loss-absorbing cushion"),
                )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["relative_selection_authority"])
        self.assertEqual(
            set(out["bound_rival_surviving_concept_ids"]),
            {regcap.CCOB, mrel.MREL},
        )
        self.assertTrue(out["opaque_remainder_required"])

    def test_pair_failure_preserves_safe_open_state(self):
        failure = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "forced",
        }
        with patch.object(v6.v5, "ground", return_value=base_for(regcap.CCYB)):
            with patch.object(v6.pair, "resolve_relative", return_value=failure):
                out = v6.ground(
                    "loss-absorbing cushion",
                    source_id="doc:fail",
                    start=0,
                    end=len("loss-absorbing cushion"),
                )
        self.assertFalse(out["relative_selection_authority"])
        self.assertIsNone(out["relative_selected_concept_id"])
        self.assertTrue(
            out["anchor_mrel_revalidation_preserved_safe_v5_open_state"]
        )

    def test_existing_v5_four_rival_selection_is_preserved(self):
        base = base_for(regcap.CCOB)
        base.update({
            "status": "OPEN__UNIQUE_REGCAP_SELECTION_RELATIVE_TO_FOUR_CONCEPT_BOUND_INVENTORY",
            "relative_selection_authority": True,
            "relative_selected_concept_id": regcap.TLAC,
        })
        with patch.object(v6.v5, "ground", return_value=base):
            with patch.object(v6.pair, "resolve_relative") as fn:
                out = v6.ground(
                    "loss-absorbing cushion",
                    source_id="doc:tlac",
                    start=0,
                    end=len("loss-absorbing cushion"),
                )
        self.assertEqual(out["relative_selected_concept_id"], regcap.TLAC)
        self.assertFalse(out["anchor_mrel_revalidation_attempted"])
        fn.assert_not_called()

    def test_stronger_source_local_identity_is_preserved(self):
        base = {
            "pass": True,
            "status": "PASS__SOURCE_LOCAL_IDENTITY",
            "semantic_identity_authority": True,
            "mapped_concept_id": regcap.CCOB,
        }
        with patch.object(v6.v5, "ground", return_value=base):
            with patch.object(v6.pair, "resolve_relative") as fn:
                out = v6.ground(
                    "loss-absorbing cushion",
                    source_id="doc:identity",
                    start=0,
                    end=len("loss-absorbing cushion"),
                )
        self.assertTrue(out["semantic_identity_authority"])
        self.assertEqual(out["mapped_concept_id"], regcap.CCOB)
        fn.assert_not_called()

    def test_wrong_frontier_never_attempts_pair_revalidation(self):
        base = base_for(regcap.CCOB)
        base["candidate_concept_ids"] = [regcap.CCOB, mrel.MREL]
        with patch.object(v6.v5, "ground", return_value=base):
            with patch.object(v6.pair, "resolve_relative") as fn:
                out = v6.ground(
                    "loss-absorbing cushion",
                    source_id="doc:wrong",
                    start=0,
                    end=len("loss-absorbing cushion"),
                )
        self.assertFalse(out["anchor_mrel_revalidation_attempted"])
        self.assertFalse(out["relative_selection_authority"])
        fn.assert_not_called()

    def test_no_global_identity_or_terminal_credit(self):
        with patch.object(v6.v5, "ground", return_value=base_for(regcap.CCYB)):
            with patch.object(
                v6.pair,
                "resolve_relative",
                return_value=pair_selected(regcap.CCYB),
            ):
                out = v6.ground(
                    "loss-absorbing cushion",
                    source_id="doc:bounds",
                    start=0,
                    end=len("loss-absorbing cushion"),
                )
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["global_phrase_identity_authority"])
        self.assertFalse(out["open_world_candidate_set_complete"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
