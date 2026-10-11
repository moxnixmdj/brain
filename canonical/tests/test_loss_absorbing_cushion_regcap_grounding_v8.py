from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v8 as g


def unresolved():
    return {
        "pass": True,
        "status": "OPEN__FOUR_WAY_CONTEXT_REMAINS_UNRESOLVED_AFTER_ALL_PAIR_REPLAY",
        "candidate_concept_ids": list(g.FOUR),
        "candidate_set_complete_relative_to_bound_inventory": True,
        "relative_selection_authority": False,
        "relative_selected_concept_id": None,
        "semantic_identity_authority": False,
        "mapped_concept_id": None,
        "minimum_policy_changing_information_request_available": True,
        "minimum_policy_changing_information_request": {"request_kind": "x"},
    }


class Tests(unittest.TestCase):
    def test_no_candidate_preserves_v7_open_state(self):
        with patch.object(g.v7, "ground", return_value=unresolved()):
            out = g.ground(
                "loss-absorbing cushion",
                source_id="doc:x",
                start=0,
                end=len("loss-absorbing cushion"),
            )
        self.assertFalse(out["authority_candidate_observation_attempted"])
        self.assertFalse(out["relative_selection_authority"])

    def test_certified_candidate_refines_original_four_way_state(self):
        observed = {
            "pass": True,
            "status": "PASS__AUTHORITY_CANDIDATE_FOUR_WAY_OBSERVATION_CERTIFIED",
            "semantic_truth_authority": True,
            "selected_concept_id": "REGCAP::MREL",
            "scope_id": "scope",
            "observation_id": "FOUR_WAY_GOVERNING_REQUIREMENT_CLASS",
            "observed_outcome": "EU_RESOLUTION_AUTHORITY_CASE_BY_CASE_MREL",
            "authority_sha256": "a" * 64,
            "raw_sha256": "b" * 64,
            "final_url": "https://example.org/mrel",
        }
        with patch.object(g.v7, "ground", return_value=unresolved()), patch.object(
            g.candidate_observation, "observe", return_value=observed
        ):
            out = g.ground(
                "loss-absorbing cushion",
                source_id="doc:x",
                start=0,
                end=len("loss-absorbing cushion"),
                governing_requirement_candidate={"chosen_url": "https://example.org/mrel"},
            )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["relative_selection_authority"])
        self.assertEqual(out["relative_selected_concept_id"], "REGCAP::MREL")
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertFalse(out["minimum_policy_changing_information_request_available"])

    def test_candidate_checker_failure_propagates_fail_closed(self):
        with patch.object(g.v7, "ground", return_value=unresolved()), patch.object(
            g.candidate_observation,
            "observe",
            return_value={"pass": False, "status": "FAIL_CLOSED", "reason": "CONFLICT"},
        ):
            out = g.ground(
                "loss-absorbing cushion",
                source_id="doc:x",
                start=0,
                end=len("loss-absorbing cushion"),
                governing_requirement_candidate={"chosen_url": "https://example.org/mrel"},
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CONFLICT", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
