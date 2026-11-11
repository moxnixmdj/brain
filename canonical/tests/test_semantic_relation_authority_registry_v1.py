from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import semantic_relation_authority_registry_v1 as r
from canonical.runtime import semantic_relation_entailment_dag_v1 as dag


def upstream(scope="finance:test", left="reserve buffer", right="liquidity cushion"):
    return {
        "pass": True,
        "schema": "PROJECT_BRAIN_SHARED_CONCEPT_IDENTITY_AUTHORITY_RECEIPT_V1",
        "scope_id": scope,
        "left_id": left,
        "right_id": right,
        "shared_concept_id": "FINANCE_ROLE::FACT",
        "left_binding_authenticated": True,
        "right_binding_authenticated": True,
        "concept_semantics_authenticated": True,
        "left_binding_sha256": "1" * 64,
        "right_binding_sha256": "2" * 64,
        "registry_sha256": "3" * 64,
        "verification_authority_mutated": False,
        "bounded_registry_scope_complete": True,
        "open_world_ontology_complete": False,
        "source_text_sha256": "4" * 64,
        "authority_git_blob_sha": "5" * 40,
        "receipt_sha256": "6" * 64,
    }


def request(**overrides):
    row = {
        "schema": r.REQUEST_SCHEMA,
        "adapter_id": r.FINANCE_BOUNDED_CONCEPT_IDENTITY_V1,
        "scope_id": "finance:test",
        "source_id": "reserve buffer",
        "target_id": "liquidity cushion",
        "relation": "ENTAILS",
        "evidence": {"schema": "PROJECT_BRAIN_FINANCE_BOUNDED_CONCEPT_IDENTITY_CLAIM_V1"},
    }
    row.update(overrides)
    return row


class SemanticRelationAuthorityRegistryV1Tests(unittest.TestCase):
    def test_finance_identity_adapts_to_canonical_entails_receipt(self):
        with patch.object(r.finance_identity, "verify_claim", return_value=upstream()):
            out = r.verify_relation(request())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["schema"], dag.RECEIPT_SCHEMA)
        self.assertEqual(out["relation"], "ENTAILS")
        self.assertTrue(out["source_semantics_authenticated"])
        self.assertTrue(out["target_semantics_authenticated"])
        self.assertTrue(out["relation_semantics_authenticated"])
        self.assertFalse(out["verification_authority_mutated"])
        self.assertFalse(out["open_world_semantic_completeness_claimed"])

    def test_finance_identity_is_symmetric_inside_exact_scope(self):
        with patch.object(r.finance_identity, "verify_claim", return_value=upstream()):
            out = r.verify_relation(request(
                source_id="liquidity cushion",
                target_id="reserve buffer",
            ))
        self.assertTrue(out["pass"], out)

    def test_wrong_scope_fails_closed(self):
        with patch.object(r.finance_identity, "verify_claim", return_value=upstream()):
            out = r.verify_relation(request(scope_id="other"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "FINANCE_IDENTITY_SCOPE_MISMATCH")

    def test_unbound_endpoint_fails_closed(self):
        with patch.object(r.finance_identity, "verify_claim", return_value=upstream()):
            out = r.verify_relation(request(target_id="other"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "FINANCE_IDENTITY_ENDPOINT_MISMATCH")

    def test_unknown_adapter_has_no_fallback(self):
        out = r.verify_relation(request(adapter_id="LLM_GUESS_V1"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "UNREGISTERED_RELATION_AUTHORITY_ADAPTER")

    def test_not_entails_is_not_invented_from_identity(self):
        with patch.object(r.finance_identity, "verify_claim", return_value=upstream()):
            out = r.verify_relation(request(relation="NOT_ENTAILS"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "FINANCE_IDENTITY_ONLY_SUPPORTS_ENTAILS")

    def test_upstream_authority_mutation_is_rejected(self):
        bad = upstream()
        bad["verification_authority_mutated"] = True
        with patch.object(r.finance_identity, "verify_claim", return_value=bad):
            out = r.verify_relation(request())
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "FINANCE_IDENTITY_UPSTREAM_AUTHORITY_NOT_PROVED")

    def test_registry_callback_closes_scoped_dag_only_with_valid_upstream(self):
        ev = {
            "schema": dag.EVIDENCE_SCHEMA,
            "scope_id": "finance:test",
            "left_id": "reserve buffer",
            "right_id": "liquidity cushion",
            "entailment_receipts": [request()],
            "counterexample_receipts": [],
        }
        with patch.object(r.finance_identity, "verify_claim", return_value=upstream()):
            out = dag.prove(
                ev,
                expected_evidence_sha256=dag.evidence_sha256(ev),
                relation_verifier=r.verify_relation,
            )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["left_entails_right"])
        self.assertEqual(out["accepted_entailment_edge_count"], 1)

    def test_registry_callback_fails_dag_for_unknown_authority(self):
        bad_request = request(adapter_id="UNREGISTERED")
        ev = {
            "schema": dag.EVIDENCE_SCHEMA,
            "scope_id": "finance:test",
            "left_id": "reserve buffer",
            "right_id": "liquidity cushion",
            "entailment_receipts": [bad_request],
            "counterexample_receipts": [],
        }
        out = dag.prove(
            ev,
            expected_evidence_sha256=dag.evidence_sha256(ev),
            relation_verifier=r.verify_relation,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("ENTAILMENT_RECEIPT_INVALID", out["reason"])

    def test_manifest_has_no_semantic_fallback(self):
        m = r.registry_manifest()
        self.assertFalse(m["fallback_semantic_inference_allowed"])
        self.assertFalse(m["caller_truth_boolean_allowed"])
        self.assertFalse(m["verification_authority_mutation_allowed"])
        self.assertFalse(m["open_world_semantic_completeness_claimed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
