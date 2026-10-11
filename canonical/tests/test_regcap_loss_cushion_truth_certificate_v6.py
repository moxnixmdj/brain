from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import regcap_loss_cushion_truth_certificate_v5 as v5
from canonical.runtime import regcap_loss_cushion_truth_certificate_v6 as v6


TEXT = "loss-absorbing cushion"
PID = v5.checked_predicate_id(
    source_id="doc:original",
    source_text=TEXT,
    start=0,
    end=len(TEXT),
    claim_kind="RELATIVE_RIVAL_SELECTION",
    target_concept_id="REGCAP::MREL",
)


def payload():
    return {
        "truth_kind": v6.TRUTH_KIND,
        "predicate_id": PID,
        "claim_kind": "RELATIVE_RIVAL_SELECTION",
        "source_text": TEXT,
        "source_id": "doc:original",
        "start": 0,
        "end": len(TEXT),
        "target_concept_id": "REGCAP::MREL",
        "governing_requirement_candidate": {
            "chosen_url": "https://example.org/mrel",
            "chosen_host": "example.org",
            "query": "mrel",
            "authority_domains": ["example.org"],
            "timeout_s": 20,
            "max_bytes": 1500000,
            "discovery_evidence_path": "x",
        },
    }


class Tests(unittest.TestCase):
    def test_v6_preserves_exact_v5_predicate_identity(self):
        self.assertIs(v6.checked_predicate_id, v5.checked_predicate_id)
        self.assertEqual(
            v6.checked_predicate_id(
                source_id="doc:original",
                source_text=TEXT,
                start=0,
                end=len(TEXT),
                claim_kind="RELATIVE_RIVAL_SELECTION",
                target_concept_id="REGCAP::MREL",
            ),
            PID,
        )

    def test_candidate_refinement_proves_original_predicate_not_a_new_one(self):
        grounded = {
            "pass": True,
            "status": "OPEN__UNIQUE_REGCAP_SELECTION_RELATIVE_TO_FOUR_CONCEPT_BOUND_INVENTORY",
            "relative_selection_authority": True,
            "relative_selected_concept_id": "REGCAP::MREL",
            "candidate_concept_ids": [
                "REGCAP::CCOB", "REGCAP::CCYB", "REGCAP::TLAC", "REGCAP::MREL"
            ],
            "semantic_identity_authority": False,
        }
        with patch.object(v6.grounding, "ground", return_value=grounded):
            out = v6.evaluate(payload())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_id"], PID)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertEqual(
            out["predicate_identity_compatibility"],
            "EXACT_V5_CHECKED_PREDICATE_ID_PRESERVED",
        )
        self.assertFalse(out["terminal_authority"])

    def test_unresolved_candidate_keeps_typed_minimum_request(self):
        request = {
            "request_kind": "ACQUIRE_ONE_AUTHENTICATED_GOVERNING_REQUIREMENT_OBSERVATION",
            "minimum_observation_count": 1,
        }
        grounded = {
            "pass": True,
            "status": "OPEN__FOUR_WAY_CONTEXT_REMAINS_UNRESOLVED_AFTER_ALL_PAIR_REPLAY",
            "relative_selection_authority": False,
            "relative_selected_concept_id": None,
            "candidate_concept_ids": [
                "REGCAP::CCOB", "REGCAP::CCYB", "REGCAP::TLAC", "REGCAP::MREL"
            ],
            "semantic_identity_authority": False,
            "minimum_policy_changing_information_request_available": True,
            "minimum_policy_changing_information_request": request,
        }
        with patch.object(v6.grounding, "ground", return_value=grounded):
            out = v6.evaluate(payload())
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_id"], PID)
        self.assertEqual(out["next_information_request"], request)


if __name__ == "__main__":
    unittest.main(verbosity=2)
