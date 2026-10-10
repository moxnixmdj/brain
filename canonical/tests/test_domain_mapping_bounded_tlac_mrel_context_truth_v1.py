from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime.domain_mapping_truth_certificate_v1 import evaluate
from canonical.runtime import tlac_mrel_identity_discriminator_v1 as pair


def candidates():
    return [
        {"concept_id": pair.TLAC},
        {"concept_id": pair.MREL},
    ]


def payload(text, target, *, scope=None, relation="LOGICAL_EQUIVALENCE_IN_SCOPE", rows=None):
    return {
        "truth_kind": "DOMAIN_MAPPING_RELATION",
        "predicate_id": "caller-id",
        "raw_span": text,
        "source_id": "doc:tlac-mrel",
        "scope_id": scope or pair.SCOPE_ID,
        "target_concept_id": target,
        "required_relation": relation,
        "candidate_concepts": candidates() if rows is None else rows,
        "relation_problems": {},
    }


def resolved(selected):
    return {
        "schema": pair.SCHEMA,
        "status": "PASS__UNIQUE_TLAC_MREL_CONCEPT_IN_BOUND_PAIR_SCOPE",
        "pass": True,
        "semantic_truth_authority": True,
        "relative_selection_authority": True,
        "candidate_universe_complete": True,
        "selected_concept_id": selected,
        "surviving_candidate_ids": [selected],
        "declared_candidate_ids": list(pair.DOMAIN),
        "global_semantic_identity_authority": False,
        "terminal_authority": False,
    }


class Tests(unittest.TestCase):
    def test_mrel_context_proves_scoped_equivalence_true(self):
        with patch.object(pair, "resolve_relative", return_value=resolved(pair.MREL)):
            out = evaluate(payload(
                "The minimum requirement for own funds and eligible liabilities "
                "shall be determined by the resolution authority.",
                pair.MREL,
            ))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertEqual(
            out["status"],
            "PASS__BOUNDED_TLAC_MREL_CONTEXT_RELATION_PROVED_TRUE",
        )
        self.assertTrue(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_tlac_context_proves_scoped_equivalence_true(self):
        with patch.object(pair, "resolve_relative", return_value=resolved(pair.TLAC)):
            out = evaluate(payload(
                "Under the FSB TLAC standard, a G-SIB must meet Minimum External TLAC.",
                pair.TLAC,
            ))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")

    def test_selected_other_pair_member_proves_target_false(self):
        with patch.object(pair, "resolve_relative", return_value=resolved(pair.MREL)):
            out = evaluate(payload(
                "The MREL requirement is set by the resolution authority.",
                pair.TLAC,
            ))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "FALSE")
        self.assertEqual(
            out["status"],
            "PASS__BOUNDED_TLAC_MREL_CONTEXT_RELATION_PROVED_FALSE",
        )

    def test_global_semantic_identity_cannot_use_pair_scope_selection(self):
        with patch.object(pair, "resolve_relative", return_value=resolved(pair.MREL)) as mocked:
            out = evaluate(payload(
                "The MREL requirement is set by the resolution authority.",
                pair.MREL,
                relation="SEMANTIC_IDENTITY",
            ))
        mocked.assert_not_called()
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertEqual(out["reason"], "TARGET_RELATION_PROBLEM_REQUIRED")

    def test_other_scope_cannot_use_pair_selection(self):
        with patch.object(pair, "resolve_relative", return_value=resolved(pair.MREL)) as mocked:
            out = evaluate(payload(
                "The MREL requirement is set by the resolution authority.",
                pair.MREL,
                scope="finance:regcap:open-world",
            ))
        mocked.assert_not_called()
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertEqual(out["reason"], "TARGET_RELATION_PROBLEM_REQUIRED")

    def test_candidate_set_mismatch_fails_closed_in_pair_scope(self):
        out = evaluate(payload(
            "Under the FSB TLAC standard, a G-SIB must meet Minimum External TLAC.",
            pair.TLAC,
            rows=[{"concept_id": pair.TLAC}],
        ))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "BOUNDED_TLAC_MREL_CONTEXT_FAIL_CLOSED",
        )

    def test_unresolved_pair_context_falls_through_to_unknown(self):
        open_result = {
            "schema": pair.SCHEMA,
            "status": "OPEN__NO_BOUND_TLAC_MREL_IDENTITY_DISCRIMINATOR",
            "pass": False,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }
        with patch.object(pair, "resolve_relative", return_value=open_result):
            out = evaluate(payload(
                "This requirement provides loss-absorbing and recapitalisation "
                "capacity available in resolution.",
                pair.TLAC,
            ))
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertEqual(out["reason"], "TARGET_RELATION_PROBLEM_REQUIRED")

    def test_pair_discriminator_fail_closed_is_propagated(self):
        bad = {
            "schema": pair.SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "PINNED_SOURCE_FRAGMENT_AUTHORITY_FAILED",
            "terminal_authority": False,
        }
        with patch.object(pair, "resolve_relative", return_value=bad):
            out = evaluate(payload(
                "Under the FSB TLAC standard, a G-SIB must meet Minimum External TLAC.",
                pair.TLAC,
            ))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "BOUNDED_TLAC_MREL_CONTEXT_FAIL_CLOSED",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
