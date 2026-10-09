from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime.domain_mapping_truth_certificate_v1 import evaluate


CCOB_TEXT = (
    "a 2.5% buffer comprised of Common Equity Tier 1 (CET1) "
    "above the regulatory minimum capital requirement"
)


def payload(raw_span=CCOB_TEXT):
    return {
        "truth_kind": "DOMAIN_MAPPING_RELATION",
        "predicate_id": "caller-id",
        "raw_span": raw_span,
        "source_id": "doc:regcap",
        "scope_id": "finance:regulatory-capital:2026",
        "target_concept_id": "REGCAP::CCOB",
        "required_relation": "SEMANTIC_IDENTITY",
        "candidate_concepts": [{
            "concept_id": "REGCAP::CCOB",
            "surface": "capital conservation buffer",
            "required_atoms": [],
            "forbidden_atoms": [],
        }],
        "relation_problems": {
            "REGCAP::CCOB": {
                "required_relation": "SEMANTIC_IDENTITY",
            }
        },
    }


class Tests(unittest.TestCase):
    def test_default_domain_mapping_auto_harvests_authenticated_regcap_context(self):
        with patch(
            "canonical.runtime.domain_mapping_truth_certificate_v1.resolve_mapping",
            return_value={
                "status": "UNRESOLVED",
                "candidate_evaluations": [],
                "semantic_truth_authority": False,
            },
        ):
            out = evaluate(payload())

        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertFalse(out["truthful_precommitment_observation"])
        ref = out["authenticated_context_refinement"]
        self.assertTrue(ref["semantic_truth_authority"])
        self.assertEqual(
            set(ref["proved_atom_ids"]),
            {
                "AMOUNT::2.5_PERCENT",
                "COMPOSITION::CET1",
                "POSITION::ABOVE_REGULATORY_MINIMUM",
            },
        )
        self.assertFalse(ref["concept_identity_claimed"])
        self.assertEqual(
            out["next_information_request"]["kind"],
            "REUSE_AUTHENTICATED_CONTEXT_FACTS_FOR_DOMAIN_MAPPING",
        )
        self.assertFalse(out["terminal_authority"])

    def test_unmatched_text_stays_unknown_without_fabricated_context(self):
        with patch(
            "canonical.runtime.domain_mapping_truth_certificate_v1.resolve_mapping",
            return_value={
                "status": "UNRESOLVED",
                "candidate_evaluations": [],
                "semantic_truth_authority": False,
            },
        ):
            out = evaluate(payload("generic loss absorbing buffer"))

        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertEqual(
            out["authenticated_context_refinement"]["proved_atom_ids"],
            [],
        )
        self.assertNotIn("next_information_request", out)

    def test_default_domain_mapping_auto_harvests_margin_rate_context(self):
        with patch(
            "canonical.runtime.domain_mapping_truth_certificate_v1.resolve_mapping",
            return_value={
                "status": "UNRESOLVED",
                "candidate_evaluations": [],
                "semantic_truth_authority": False,
            },
        ):
            out = evaluate(payload(
                "The margin is added to the specified index rate."
            ))

        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        ref = out["authenticated_context_refinement"]
        self.assertTrue(ref["semantic_truth_authority"])
        self.assertEqual(
            ref["proved_atom_ids"],
            ["FINANCE_MARGIN_CONTEXT::INDEX_RATE_ADD_ON"],
        )
        self.assertIn(
            "CERTIFIED_FINANCE_MARGIN_CONTEXT",
            ref["accepted_context_kinds"],
        )
        self.assertFalse(ref["concept_identity_claimed"])
        self.assertEqual(
            out["next_information_request"]["kind"],
            "REUSE_AUTHENTICATED_CONTEXT_FACTS_FOR_DOMAIN_MAPPING",
        )

    def test_bare_margin_stays_unknown_without_context_atom(self):
        with patch(
            "canonical.runtime.domain_mapping_truth_certificate_v1.resolve_mapping",
            return_value={
                "status": "UNRESOLVED",
                "candidate_evaluations": [],
                "semantic_truth_authority": False,
            },
        ):
            out = evaluate(payload("Margin increased."))

        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertEqual(
            out["authenticated_context_refinement"]["proved_atom_ids"],
            [],
        )
        self.assertNotIn("next_information_request", out)

    def test_context_facts_never_upgrade_unproved_identity_to_true(self):
        with patch(
            "canonical.runtime.domain_mapping_truth_certificate_v1.resolve_mapping",
            return_value={
                "status": "UNRESOLVED",
                "candidate_evaluations": [{
                    "concept_id": "REGCAP::CCOB",
                    "relation_result": {
                        "pass": False,
                        "required_relation": "SEMANTIC_IDENTITY",
                        "status": "OPEN__REQUIRED_RELATION_UNPROVED",
                    },
                }],
                "semantic_truth_authority": False,
            },
        ):
            out = evaluate(payload())

        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertFalse(out["authenticated_context_refinement"]["concept_identity_claimed"])
        self.assertFalse(out["semantic_truth_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
