from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v7 as v7
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel
from canonical.runtime import regcap_mrel_pair_discriminator_v1 as regpair


FOUR = sorted([regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL])


def unresolved_v6():
    return {
        "schema": "PROJECT_BRAIN_LOSS_ABSORBING_CUSHION_REGCAP_GROUNDING_V6",
        "status": "OPEN__ANCHOR_MREL_PAIR_REMAINS_UNRESOLVED",
        "pass": True,
        "candidate_concept_ids": list(FOUR),
        "candidate_set_complete_relative_to_bound_inventory": True,
        "relative_selection_authority": False,
        "relative_selected_concept_id": None,
        "semantic_identity_authority": False,
        "mapped_concept_id": None,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def pair(selected=None, *, fail=False):
    if fail:
        return {"status": "FAIL_CLOSED", "pass": False, "reason": "SOURCE_DRIFT"}
    if selected is None:
        return {
            "status": "OPEN__NO_BOUND_PAIR_CONTEXT_SIGNATURE",
            "pass": False,
            "relative_selection_authority": False,
        }
    return {
        "status": "PASS__UNIQUE_CONCEPT_IN_BOUND_PAIR_SCOPE",
        "pass": True,
        "semantic_truth_authority": True,
        "relative_selection_authority": True,
        "selected_concept_id": selected,
        "surviving_candidate_ids": [selected],
    }


class Tests(unittest.TestCase):
    def test_unanimous_mrel_across_all_three_pairs_lifts_to_four_way_relative_selection(self):
        with patch.object(v7.v6, "ground", return_value=unresolved_v6()), patch.object(
            v7.regpair, "resolve_relative", return_value=pair(mrel.MREL)
        ) as rp, patch.object(
            v7.tlacpair, "resolve_relative", return_value=pair(mrel.MREL)
        ) as tp:
            out = v7.ground("x", source_id="s", start=0, end=1)

        self.assertTrue(out["pass"], out)
        self.assertTrue(out["relative_selection_authority"])
        self.assertEqual(out["relative_selected_concept_id"], mrel.MREL)
        self.assertEqual(out["bound_rival_surviving_concept_ids"], [mrel.MREL])
        self.assertTrue(out["four_concept_relative_selection_reproved"])
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["candidate_universe_complete"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(rp.call_count, 2)
        tp.assert_called_once()

    def test_one_open_pair_preserves_four_way_ambiguity(self):
        def resolve(*args, **kwargs):
            if kwargs["pair_id"] == regpair.CCOB_MREL:
                return pair(None)
            return pair(mrel.MREL)

        with patch.object(v7.v6, "ground", return_value=unresolved_v6()), patch.object(
            v7.regpair, "resolve_relative", side_effect=resolve
        ), patch.object(v7.tlacpair, "resolve_relative", return_value=pair(mrel.MREL)):
            out = v7.ground("x", source_id="s", start=0, end=1)

        self.assertTrue(out["pass"])
        self.assertFalse(out["relative_selection_authority"])
        self.assertEqual(
            out["status"],
            "OPEN__FOUR_WAY_CONTEXT_REMAINS_UNRESOLVED_AFTER_ALL_PAIR_REPLAY",
        )
        self.assertEqual(out["bound_rival_surviving_concept_ids"], FOUR)

    def test_mixed_mrel_and_regcap_pair_selection_fails_closed(self):
        calls = iter([pair(regcap.CCOB), pair(mrel.MREL)])
        with patch.object(v7.v6, "ground", return_value=unresolved_v6()), patch.object(
            v7.regpair, "resolve_relative", side_effect=lambda *a, **k: next(calls)
        ), patch.object(v7.tlacpair, "resolve_relative", return_value=pair(mrel.MREL)):
            out = v7.ground("x", source_id="s", start=0, end=1)

        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "CONFLICTING_ALL_PAIR_CONTEXT_SELECTIONS")

    def test_any_pair_fail_closed_propagates_fail_closed(self):
        with patch.object(v7.v6, "ground", return_value=unresolved_v6()), patch.object(
            v7.regpair, "resolve_relative", side_effect=[pair(fail=True), pair(mrel.MREL)]
        ), patch.object(v7.tlacpair, "resolve_relative", return_value=pair(mrel.MREL)):
            out = v7.ground("x", source_id="s", start=0, end=1)

        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("PAIR_REPLAY_FAIL_CLOSED", out["reason"])

    def test_existing_v6_relative_selection_bypasses_all_pair_lift(self):
        base = unresolved_v6()
        base["relative_selection_authority"] = True
        base["relative_selected_concept_id"] = regcap.CCOB
        base["bound_rival_surviving_concept_ids"] = [regcap.CCOB]
        with patch.object(v7.v6, "ground", return_value=base), patch.object(
            v7.regpair, "resolve_relative"
        ) as rp, patch.object(v7.tlacpair, "resolve_relative") as tp:
            out = v7.ground("x", source_id="s", start=0, end=1)
        self.assertEqual(out["relative_selected_concept_id"], regcap.CCOB)
        self.assertFalse(out["all_pairs_mrel_lift_attempted"])
        rp.assert_not_called()
        tp.assert_not_called()

    def test_inexact_four_way_inventory_never_lifts(self):
        base = unresolved_v6()
        base["candidate_concept_ids"] = [regcap.TLAC, mrel.MREL]
        with patch.object(v7.v6, "ground", return_value=base), patch.object(
            v7.regpair, "resolve_relative"
        ) as rp, patch.object(v7.tlacpair, "resolve_relative") as tp:
            out = v7.ground("x", source_id="s", start=0, end=1)
        self.assertFalse(out["all_pairs_mrel_lift_attempted"])
        self.assertEqual(
            out["all_pairs_mrel_lift_reason"],
            "EXACT_FOUR_CONCEPT_BOUND_INVENTORY_REQUIRED",
        )
        rp.assert_not_called()
        tp.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
