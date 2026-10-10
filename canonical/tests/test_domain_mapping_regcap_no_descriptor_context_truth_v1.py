from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime.domain_mapping_truth_certificate_v1 import evaluate
from canonical.runtime import regcap_bounded_rival_registry_authority_v1 as registry
from canonical.runtime import regcap_contrastive_discriminator_matrix_v1 as matrix


def candidate_rows():
    return [{"concept_id": cid} for cid in matrix.DOMAIN]


def fake_projection(pack):
    return {
        "pass": True,
        "receipt": {
            "fragment_ids": sorted(
                str(row["fragment_id"])
                for row in pack.get("fragments", [])
            ),
            "receipt_sha256": "a" * 64,
        },
        "source_fragment_authority": True,
        "terminal_authority": False,
    }


def fake_universe():
    checked = matrix.load_pack()
    source_results = {
        sid: fake_projection(pack)
        for sid, pack in checked["sources_by_id"].items()
    }
    return {
        "status": "OPEN__AUTHENTICATED_BOUNDED_CONCEPT_UNIVERSE_NEEDS_DISCRIMINATOR",
        "pass": False,
        "authenticated_scope_completeness": True,
        "hypothesis_set_complete": True,
        "candidate_set_complete_relative_to_registry": True,
        "candidate_concept_ids": list(matrix.DOMAIN),
        "authority_result": {
            "pass": True,
            "matrix_result": {
                "pass": True,
                "candidate_domain": list(matrix.DOMAIN),
                "observations": [
                    {
                        "observation_id": oid,
                        "outcomes": dict(outcomes),
                    }
                    for oid, outcomes in matrix.OBSERVATIONS.items()
                ],
                "matrix_sha256": "b" * 64,
                "source_results": source_results,
            },
        },
        "semantic_truth_authority": False,
        "terminal_authority": False,
    }


def payload(text, target, *, relation="LOGICAL_EQUIVALENCE_IN_SCOPE", scope=None, candidates=None):
    return {
        "truth_kind": "DOMAIN_MAPPING_RELATION",
        "predicate_id": "caller-id",
        "raw_span": text,
        "source_id": "doc:regcap:no-descriptor",
        "scope_id": scope or registry.SCOPE_ID,
        "target_concept_id": target,
        "required_relation": relation,
        "candidate_concepts": candidate_rows() if candidates is None else candidates,
        "relation_problems": {},
    }


class Tests(unittest.TestCase):
    def _evaluate(self, row):
        with patch.object(
            registry,
            "resolve_authenticated_registry",
            return_value=fake_universe(),
        ):
            return evaluate(row)

    def test_ccob_direct_structure_without_descriptor_proves_scoped_equivalence(self):
        text = "The cushion is 2.5% CET1 above the regulatory minimum."
        out = self._evaluate(payload(text, "REGCAP::CCOB"))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertEqual(
            out["status"],
            "PASS__BOUNDED_REGCAP_NO_DESCRIPTOR_CONTEXT_RELATION_PROVED_TRUE",
        )
        self.assertFalse(out["terminal_authority"])

    def test_ccyb_direct_release_without_descriptor_proves_scoped_equivalence(self):
        text = "The cushion is released when system-wide risk crystallises or dissipates."
        out = self._evaluate(payload(text, "REGCAP::CCYB"))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")

    def test_tlac_direct_resolution_signature_without_descriptor_proves_scoped_equivalence(self):
        text = (
            "The capacity provides loss-absorbing and recapitalisation capacity "
            "available in resolution for a failing G-SIB."
        )
        out = self._evaluate(payload(text, "REGCAP::TLAC"))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")

    def test_unique_other_candidate_proves_target_false(self):
        text = "The cushion is released when system-wide risk crystallises or dissipates."
        out = self._evaluate(payload(text, "REGCAP::CCOB"))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "FALSE")
        self.assertEqual(
            out["status"],
            "PASS__BOUNDED_REGCAP_NO_DESCRIPTOR_CONTEXT_RELATION_PROVED_FALSE",
        )

    def test_global_semantic_identity_does_not_use_bounded_no_descriptor_path(self):
        text = "The cushion is released when system-wide risk crystallises or dissipates."
        out = self._evaluate(
            payload(
                text,
                "REGCAP::CCYB",
                relation="SEMANTIC_IDENTITY",
            )
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")

    def test_other_scope_does_not_use_bounded_no_descriptor_path(self):
        text = "The cushion is released when system-wide risk crystallises or dissipates."
        out = self._evaluate(
            payload(
                text,
                "REGCAP::CCYB",
                scope="finance:regulatory-capital:open-world",
            )
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")

    def test_candidate_set_mismatch_fails_closed(self):
        text = "The cushion is released when system-wide risk crystallises or dissipates."
        out = self._evaluate(
            payload(
                text,
                "REGCAP::CCYB",
                candidates=[
                    {"concept_id": "REGCAP::CCOB"},
                    {"concept_id": "REGCAP::CCYB"},
                ],
            )
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "BOUNDED_REGCAP_NO_DESCRIPTOR_CONTEXT_FAIL_CLOSED",
        )

    def test_partial_context_stays_unknown(self):
        text = "The cushion is released when risk dissipates."
        out = self._evaluate(payload(text, "REGCAP::CCYB"))
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")

    def test_registry_authority_failure_fails_closed(self):
        text = "The cushion is released when system-wide risk crystallises or dissipates."
        with patch.object(
            registry,
            "resolve_authenticated_registry",
            return_value={"status": "FAIL_CLOSED", "pass": False},
        ):
            out = evaluate(payload(text, "REGCAP::CCYB"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "BOUNDED_REGCAP_NO_DESCRIPTOR_CONTEXT_FAIL_CLOSED",
        )

    def test_no_global_or_terminal_authority(self):
        text = "The cushion is 2.5% CET1 above the regulatory minimum."
        out = self._evaluate(payload(text, "REGCAP::CCOB"))
        self.assertTrue(out["pass"], out)
        rel = out["bounded_no_descriptor_context_relation"]
        self.assertFalse(rel["global_semantic_identity_authority"])
        self.assertFalse(rel["open_world_candidate_set_complete"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
