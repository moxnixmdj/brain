import unittest

from canonical.runtime.semantic_relation_control_v1 import (
    make_proof_record,
    resolve,
)


SCOPE = "finance:policy:2026"


def proof(kind, **evidence):
    return make_proof_record(
        kind=kind,
        scope_id=SCOPE,
        verifier_id="independent:test-verifier",
        evidence=evidence or {"source": "test"},
    )


class Tests(unittest.TestCase):
    def test_similarity_candidate_never_certifies_equivalence(self):
        out = resolve({
            "left_id": "reserve-buffer",
            "right_id": "liquidity-cushion",
            "scope_id": SCOPE,
            "required_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
            "proof_records": [],
            "candidate_relations": [
                {"relation": "SIMILAR", "score": 0.99, "source": "embedding"}
            ],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["strongest_proved_relation"], "UNKNOWN")
        self.assertFalse(out["candidate_relations_are_authority"])

    def test_explicit_scoped_equivalence_proves_identity_only_in_scope(self):
        out = resolve({
            "left_id": "reserve-buffer",
            "right_id": "liquidity-cushion",
            "scope_id": SCOPE,
            "required_relation": "SEMANTIC_IDENTITY",
            "proof_records": [
                proof("EXPLICIT_SCOPED_EQUIVALENCE", source_id="doc:A")
            ],
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["strongest_proved_relation"], "SEMANTIC_IDENTITY")
        self.assertFalse(out["scope_leakage_authorized"])

    def test_same_authority_concept_id_proves_scoped_identity(self):
        out = resolve({
            "left_id": "reserve-buffer",
            "right_id": "liquidity-cushion",
            "scope_id": SCOPE,
            "required_relation": "SEMANTIC_IDENTITY",
            "proof_records": [
                proof(
                    "SAME_AUTHORITY_CONCEPT_ID",
                    authority="regulator-X",
                    concept_id="capital-buffer:17",
                )
            ],
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["strongest_proved_relation"], "SEMANTIC_IDENTITY")

    def test_mutual_entailment_proves_logical_not_identity(self):
        out = resolve({
            "left_id": "A",
            "right_id": "B",
            "scope_id": SCOPE,
            "required_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
            "proof_records": [
                proof("LEFT_ENTAILS_RIGHT", proof_id="p1"),
                proof("RIGHT_ENTAILS_LEFT", proof_id="p2"),
            ],
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["strongest_proved_relation"],
            "LOGICAL_EQUIVALENCE_IN_SCOPE",
        )
        self.assertFalse(out["proved_facts"]["semantic_identity"])

    def test_one_way_entailment_is_not_upgraded_to_equivalence(self):
        out = resolve({
            "left_id": "CET1-capital",
            "right_id": "regulatory-capital",
            "scope_id": SCOPE,
            "required_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
            "proof_records": [proof("LEFT_ENTAILS_RIGHT")],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["strongest_proved_relation"], "LEFT_ENTAILS_RIGHT")

    def test_complete_terminal_signature_equality_is_enough_for_current_decision(self):
        out = resolve({
            "left_id": "reserve-buffer",
            "right_id": "liquidity-cushion",
            "scope_id": SCOPE,
            "required_relation": "CURRENT_DECISION_SUBSTITUTION",
            "proof_records": [],
            "terminal_signature_rows": [
                {
                    "raw_id": "reserve-buffer",
                    "signature_complete": True,
                    "terminal_signature": {
                        "threshold": 10,
                        "action_below": "REDUCE_EXPOSURE",
                    },
                },
                {
                    "raw_id": "liquidity-cushion",
                    "signature_complete": True,
                    "terminal_signature": {
                        "threshold": 10,
                        "action_below": "REDUCE_EXPOSURE",
                    },
                },
            ],
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["strongest_proved_relation"],
            "CURRENT_DECISION_SUBSTITUTION",
        )
        self.assertFalse(out["proved_facts"]["semantic_identity"])

    def test_task_equivalence_does_not_prove_semantic_identity(self):
        out = resolve({
            "left_id": "A",
            "right_id": "B",
            "scope_id": SCOPE,
            "required_relation": "SEMANTIC_IDENTITY",
            "proof_records": [],
            "terminal_signature_rows": [
                {
                    "raw_id": "A",
                    "signature_complete": True,
                    "terminal_signature": {"action": "ALLOW"},
                },
                {
                    "raw_id": "B",
                    "signature_complete": True,
                    "terminal_signature": {"action": "ALLOW"},
                },
            ],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["strongest_proved_relation"],
            "CURRENT_DECISION_SUBSTITUTION",
        )

    def test_terminal_difference_blocks_task_substitution(self):
        out = resolve({
            "left_id": "A",
            "right_id": "B",
            "scope_id": SCOPE,
            "required_relation": "CURRENT_DECISION_SUBSTITUTION",
            "proof_records": [],
            "terminal_signature_rows": [
                {
                    "raw_id": "A",
                    "signature_complete": True,
                    "terminal_signature": {"action": "ALLOW"},
                },
                {
                    "raw_id": "B",
                    "signature_complete": True,
                    "terminal_signature": {"action": "DENY"},
                },
            ],
        })
        self.assertFalse(out["pass"])
        self.assertFalse(out["proved_facts"]["current_decision_substitution"])

    def test_verified_counterexample_conflicting_with_positive_proof_fails_closed(self):
        out = resolve({
            "left_id": "A",
            "right_id": "B",
            "scope_id": SCOPE,
            "required_relation": "SEMANTIC_IDENTITY",
            "proof_records": [
                proof("EXPLICIT_SCOPED_EQUIVALENCE"),
                proof("IDENTITY_COUNTEREXAMPLE"),
            ],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__SEMANTIC_EVIDENCE_CONFLICT",
        )

    def test_wrong_scope_proof_is_rejected(self):
        row = make_proof_record(
            kind="LEFT_ENTAILS_RIGHT",
            scope_id="different-scope",
            verifier_id="v",
            evidence={"x": 1},
        )
        out = resolve({
            "left_id": "A",
            "right_id": "B",
            "scope_id": SCOPE,
            "required_relation": "LEFT_ENTAILS_RIGHT",
            "proof_records": [row],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED__INVALID_PROOF_RECORD")

    def test_tampered_proof_is_rejected(self):
        row = proof("LEFT_ENTAILS_RIGHT")
        row["evidence"]["tampered"] = True
        out = resolve({
            "left_id": "A",
            "right_id": "B",
            "scope_id": SCOPE,
            "required_relation": "LEFT_ENTAILS_RIGHT",
            "proof_records": [row],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED__INVALID_PROOF_RECORD")


if __name__ == "__main__":
    unittest.main(verbosity=2)
