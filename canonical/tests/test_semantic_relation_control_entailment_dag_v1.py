import unittest

from canonical.runtime.semantic_relation_control_v1 import resolve
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA,
    RECEIPT_SCHEMA,
    evidence_sha256,
)


SCOPE = "finance:policy:2026"


def receipt(source, target, relation="ENTAILS"):
    return {
        "pass": True,
        "schema": RECEIPT_SCHEMA,
        "scope_id": SCOPE,
        "source_id": source,
        "target_id": target,
        "relation": relation,
        "source_semantics_authenticated": True,
        "target_semantics_authenticated": True,
        "relation_semantics_authenticated": True,
        "verification_authority_mutated": False,
        "evidence_sha256": "a" * 64,
        "receipt_sha256": "b" * 64,
    }


def dag(edges=(), counters=(), left="A", right="B"):
    return {
        "schema": EVIDENCE_SCHEMA,
        "scope_id": SCOPE,
        "left_id": left,
        "right_id": right,
        "entailment_receipts": list(edges),
        "counterexample_receipts": list(counters),
    }


class Tests(unittest.TestCase):
    def test_transitive_dag_proves_directional_relation_without_complete_universe(self):
        evidence = dag([receipt("A", "X"), receipt("X", "B")])
        out = resolve(
            {
                "left_id": "A",
                "right_id": "B",
                "scope_id": SCOPE,
                "required_relation": "LEFT_ENTAILS_RIGHT",
                "entailment_dag_evidence": evidence,
                "expected_entailment_dag_sha256": evidence_sha256(evidence),
            },
            relation_edge_verifier=lambda value: value,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["strongest_proved_relation"], "LEFT_ENTAILS_RIGHT")
        self.assertEqual(
            out["entailment_dag_proof"]["left_to_right_path"],
            ["A", "X", "B"],
        )

    def test_mutual_entailment_dag_proves_scoped_logical_equivalence_not_identity(self):
        evidence = dag([
            receipt("A", "X"),
            receipt("X", "B"),
            receipt("B", "Y"),
            receipt("Y", "A"),
        ])
        out = resolve(
            {
                "left_id": "A",
                "right_id": "B",
                "scope_id": SCOPE,
                "required_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
                "entailment_dag_evidence": evidence,
                "expected_entailment_dag_sha256": evidence_sha256(evidence),
            },
            relation_edge_verifier=lambda value: value,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["strongest_proved_relation"],
            "LOGICAL_EQUIVALENCE_IN_SCOPE",
        )
        self.assertFalse(out["proved_facts"]["semantic_identity"])

    def test_authenticated_counterexample_disproves_requested_entailment(self):
        evidence = dag([], [receipt("A", "B", "NOT_ENTAILS")])
        out = resolve(
            {
                "left_id": "A",
                "right_id": "B",
                "scope_id": SCOPE,
                "required_relation": "LEFT_ENTAILS_RIGHT",
                "entailment_dag_evidence": evidence,
                "expected_entailment_dag_sha256": evidence_sha256(evidence),
            },
            relation_edge_verifier=lambda value: value,
        )
        self.assertFalse(out["pass"])
        self.assertTrue(out["required_relation_disproved"])
        self.assertEqual(
            out["status"],
            "PROVED__REQUIRED_SEMANTIC_RELATION_FALSE_IN_BOUND_SCOPE",
        )
        self.assertEqual(out["next_proof_targets"], [])

    def test_dag_receipt_without_authority_verifier_fails_closed(self):
        evidence = dag([receipt("A", "B")])
        out = resolve({
            "left_id": "A",
            "right_id": "B",
            "scope_id": SCOPE,
            "required_relation": "LEFT_ENTAILS_RIGHT",
            "entailment_dag_evidence": evidence,
            "expected_entailment_dag_sha256": evidence_sha256(evidence),
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED__ENTAILMENT_DAG_EVIDENCE_INVALID")

    def test_similarity_candidate_cannot_override_counterexample(self):
        evidence = dag([], [receipt("A", "B", "NOT_ENTAILS")])
        out = resolve(
            {
                "left_id": "A",
                "right_id": "B",
                "scope_id": SCOPE,
                "required_relation": "LEFT_ENTAILS_RIGHT",
                "candidate_relations": [
                    {"relation": "SYNONYM", "score": 0.999, "source": "model"}
                ],
                "entailment_dag_evidence": evidence,
                "expected_entailment_dag_sha256": evidence_sha256(evidence),
            },
            relation_edge_verifier=lambda value: value,
        )
        self.assertFalse(out["pass"])
        self.assertTrue(out["required_relation_disproved"])
        self.assertFalse(out["candidate_relations_are_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
