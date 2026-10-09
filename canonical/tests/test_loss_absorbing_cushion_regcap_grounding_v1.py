from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v1 as grounding
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import regcap_property_candidate_discovery_v1 as discovery


RAW = "loss-absorbing cushion"


def discovery_result(ids=None):
    ids = ids or [regcap.CCOB, regcap.CCYB, regcap.TLAC]
    return {
        "pass": True,
        "status": (
            "OPEN__NON_UNIQUE_PROPERTY_CANDIDATES"
            if len(ids) > 1
            else "OPEN__SINGLE_PROPERTY_CANDIDATE_NOT_IDENTITY"
        ),
        "candidate_generation_authority": True,
        "candidate_concept_ids": list(ids),
        "candidates": [
            {
                "concept_id": cid,
                "positive_evidence_targets": {
                    regcap.CCOB: ["POSITION::ABOVE_REGULATORY_MINIMUM"],
                    regcap.CCYB: ["TRIGGER::EXCESS_CREDIT_GROWTH_SYSTEM_WIDE_RISK"],
                    regcap.TLAC: ["REGIME::RESOLUTION"],
                }[cid],
            }
            for cid in ids
        ],
    }


class Tests(unittest.TestCase):
    def test_exact_phrase_proves_property_and_returns_nonunique_candidates(self):
        with patch.object(
            grounding.discovery,
            "discover",
            return_value=discovery_result(),
        ):
            out = grounding.ground(
                RAW,
                source_id="doc:A",
                start=0,
                end=len(RAW),
            )

        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "OPEN__COMPOSED_SOURCE_MEANING_WITH_NON_UNIQUE_REGCAP_CANDIDATES",
        )
        self.assertTrue(out["source_constraint_proved"])
        self.assertEqual(
            out["proved_source_constraints"],
            [{"op": "ATOM", "id": "DISPOSITION::LOSS_ABSORPTION"}],
        )
        self.assertEqual(
            out["candidate_concept_ids"],
            [regcap.CCOB, regcap.CCYB, regcap.TLAC],
        )
        self.assertTrue(out["non_unique_property_witness"])
        self.assertIsNone(out["mapped_concept_id"])
        self.assertTrue(out["opaque_remainder_required"])
        self.assertFalse(out["fully_semantically_bound"])

    def test_exact_embedded_span_works_without_absorbing_surrounding_context(self):
        text = "The bank maintains a loss-absorbing cushion during stress."
        start = text.index(RAW)
        with patch.object(
            grounding.discovery,
            "discover",
            return_value=discovery_result(),
        ):
            out = grounding.ground(
                text,
                source_id="doc:A",
                start=start,
                end=start + len(RAW),
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["raw_span"], RAW)

    def test_non_hyphenated_phrase_remains_unresolved(self):
        text = "loss absorbing cushion"
        with patch.object(
            grounding.discovery,
            "discover",
            return_value=discovery_result(),
        ) as mocked:
            out = grounding.ground(
                text,
                source_id="doc:A",
                start=0,
                end=len(text),
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__SOURCE_SEMANTICS_UNRESOLVED")
        mocked.assert_not_called()

    def test_single_candidate_still_not_identity(self):
        with patch.object(
            grounding.discovery,
            "discover",
            return_value=discovery_result([regcap.TLAC]),
        ):
            out = grounding.ground(
                RAW,
                source_id="doc:A",
                start=0,
                end=len(RAW),
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "OPEN__COMPOSED_SOURCE_MEANING_WITH_SINGLE_NONIDENTITY_CANDIDATE",
        )
        self.assertEqual(out["candidate_concept_ids"], [regcap.TLAC])
        self.assertIsNone(out["mapped_concept_id"])
        self.assertFalse(out["semantic_identity_authority"])

    def test_candidate_discovery_fail_closed_propagates(self):
        with patch.object(
            grounding.discovery,
            "discover",
            return_value={
                "pass": False,
                "status": "FAIL_CLOSED",
                "reason": "SOURCE_AUTHORITY_FAILURE",
            },
        ):
            out = grounding.ground(
                RAW,
                source_id="doc:A",
                start=0,
                end=len(RAW),
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "CANDIDATE_DISCOVERY_FAIL_CLOSED")

    def test_no_candidate_does_not_mean_nonexistence(self):
        with patch.object(
            grounding.discovery,
            "discover",
            return_value={
                "pass": False,
                "status": "OPEN__NO_VERIFIED_PROPERTY_CANDIDATES_IN_BOUND_RIVAL_SET",
                "candidate_generation_authority": True,
                "candidate_concept_ids": [],
            },
        ):
            out = grounding.ground(
                RAW,
                source_id="doc:A",
                start=0,
                end=len(RAW),
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__PROVED_SOURCE_PROPERTY_WITHOUT_VERIFIED_REGCAP_CANDIDATES",
        )
        self.assertFalse(out["no_candidate_means_nonexistence"])

    def test_no_semantic_identity_or_terminal_authority(self):
        with patch.object(
            grounding.discovery,
            "discover",
            return_value=discovery_result(),
        ):
            out = grounding.ground(
                RAW,
                source_id="doc:A",
                start=0,
                end=len(RAW),
            )
        self.assertTrue(out["candidate_generation_authority"])
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
