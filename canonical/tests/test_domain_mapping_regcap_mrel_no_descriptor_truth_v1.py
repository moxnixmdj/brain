from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime.domain_mapping_truth_certificate_v1 import evaluate
from canonical.runtime import regcap_mrel_pair_discriminator_v1 as pair
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel
from canonical.runtime import regcap_mrel_no_descriptor_pair_v1 as nd


def payload(text, pair_id, target):
    return {
        "truth_kind": "DOMAIN_MAPPING_RELATION",
        "predicate_id": "caller-label",
        "raw_span": text,
        "source_id": "doc:pair-no-descriptor",
        "scope_id": pair.PAIR_SCOPE[pair_id],
        "target_concept_id": target,
        "required_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
        "candidate_concepts": [
            {"concept_id": cid}
            for cid in pair.PAIR_DOMAIN[pair_id]
        ],
        "relation_problems": {},
    }


def resolved(pair_id, selected):
    return {
        "schema": nd.SCHEMA,
        "status": "PASS__UNIQUE_CONCEPT_IN_BOUND_REGCAP_MREL_NO_DESCRIPTOR_PAIR_SCOPE",
        "pass": True,
        "semantic_truth_authority": True,
        "relative_selection_authority": True,
        "pair_id": pair_id,
        "candidate_universe_complete": True,
        "selected_concept_id": selected,
        "surviving_candidate_ids": [selected],
        "declared_candidate_ids": list(pair.PAIR_DOMAIN[pair_id]),
        "terminal_authority": False,
    }


class Tests(unittest.TestCase):
    def test_ccob_pair_true_reaches_domain_truth(self):
        with patch.object(
            nd,
            "resolve_relative",
            return_value=resolved(pair.CCOB_MREL, regcap.CCOB),
        ):
            out = evaluate(
                payload(
                    "The cushion is 2.5% CET1 above the regulatory minimum.",
                    pair.CCOB_MREL,
                    regcap.CCOB,
                )
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertEqual(
            out["status"],
            "PASS__BOUNDED_REGCAP_MREL_NO_DESCRIPTOR_CONTEXT_RELATION_PROVED_TRUE",
        )

    def test_unique_other_candidate_proves_false(self):
        with patch.object(
            nd,
            "resolve_relative",
            return_value=resolved(pair.CCOB_MREL, regcap.CCOB),
        ):
            out = evaluate(
                payload(
                    "The cushion is 2.5% CET1 above the regulatory minimum.",
                    pair.CCOB_MREL,
                    mrel.MREL,
                )
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "FALSE")

    def test_mrel_pair_true_reaches_domain_truth(self):
        with patch.object(
            nd,
            "resolve_relative",
            return_value=resolved(pair.CCYB_MREL, mrel.MREL),
        ):
            out = evaluate(
                payload(
                    "The minimum requirement for own funds and eligible liabilities "
                    "shall be determined by the resolution authority under Article 45c.",
                    pair.CCYB_MREL,
                    mrel.MREL,
                )
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")

    def test_ccyb_pair_true_reaches_domain_truth(self):
        with patch.object(
            nd,
            "resolve_relative",
            return_value=resolved(pair.CCYB_MREL, regcap.CCYB),
        ):
            out = evaluate(
                payload(
                    "The cushion is released when system-wide risk crystallises or dissipates.",
                    pair.CCYB_MREL,
                    regcap.CCYB,
                )
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")

    def test_open_pair_remains_unknown(self):
        with patch.object(
            nd,
            "resolve_relative",
            return_value={
                "schema": nd.SCHEMA,
                "status": "OPEN__NO_BOUND_NO_DESCRIPTOR_PAIR_CONTEXT_SIGNATURE",
                "pass": False,
                "semantic_truth_authority": False,
                "terminal_authority": False,
            },
        ):
            out = evaluate(
                payload(
                    "The requirement absorbs losses.",
                    pair.CCOB_MREL,
                    regcap.CCOB,
                )
            )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")

    def test_pair_conflict_fails_closed(self):
        with patch.object(
            nd,
            "resolve_relative",
            return_value={
                "schema": nd.SCHEMA,
                "status": "FAIL_CLOSED",
                "pass": False,
                "reason": "CONFLICTING_NO_DESCRIPTOR_PAIR_CONTEXT_SIGNATURES",
                "semantic_truth_authority": False,
                "terminal_authority": False,
            },
        ):
            out = evaluate(
                payload(
                    "Conflicting context.",
                    pair.CCOB_MREL,
                    regcap.CCOB,
                )
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "BOUNDED_REGCAP_MREL_NO_DESCRIPTOR_CONTEXT_FAIL_CLOSED",
        )

    def test_wrong_candidate_pair_fails_closed_before_resolver(self):
        row = payload(
            "The cushion is 2.5% CET1 above the regulatory minimum.",
            pair.CCOB_MREL,
            regcap.CCOB,
        )
        row["candidate_concepts"] = [{"concept_id": regcap.CCOB}]
        out = evaluate(row)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "BOUNDED_REGCAP_MREL_NO_DESCRIPTOR_CONTEXT_FAIL_CLOSED",
        )

    def test_no_global_or_terminal_authority(self):
        with patch.object(
            nd,
            "resolve_relative",
            return_value=resolved(pair.CCOB_MREL, regcap.CCOB),
        ):
            out = evaluate(
                payload(
                    "The cushion is 2.5% CET1 above the regulatory minimum.",
                    pair.CCOB_MREL,
                    regcap.CCOB,
                )
            )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_truth_authority"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)
        route = out["bounded_regcap_mrel_no_descriptor_context_relation"]
        self.assertFalse(route["global_semantic_identity_authority"])
        self.assertFalse(route["open_world_candidate_set_complete"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
