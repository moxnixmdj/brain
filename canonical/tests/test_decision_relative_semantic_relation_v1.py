import unittest

from canonical.runtime.decision_relative_semantic_relation_v1 import prove


SCOPE = "1" * 64


def receipt(relation, source_kind="CHECKED_PROOF_DAG", scope=SCOPE):
    return {
        "verified": True,
        "relation": relation,
        "source_kind": source_kind,
        "verifier_id": "verifier:test",
        "evidence_sha256": "e" * 64,
        "scope_sha256": scope,
    }


def terminal_rows(a, b):
    return [
        {"raw_id": "A", "signature_complete": True, "terminal_signature": a},
        {"raw_id": "B", "signature_complete": True, "terminal_signature": b},
    ]


class Tests(unittest.TestCase):
    def test_explicit_source_equivalence_proves_exact_equivalence(self):
        out = prove({
            "expression_a": "reserve buffer",
            "expression_b": "liquidity cushion",
            "required_relation": "BIDIRECTIONAL_EQUIVALENCE",
            "scope_sha256": SCOPE,
            "evidence": {"explicit_source_equivalence": receipt("EXACT_EQUIVALENT", "EXPLICIT_SOURCE_DEFINITION")},
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["strongest_proved_relation"], "EXACT_EQUIVALENT")

    def test_same_authenticated_concept_id_proves_exact_equivalence(self):
        out = prove({
            "expression_a": "reserve buffer",
            "expression_b": "liquidity cushion",
            "required_relation": "BIDIRECTIONAL_EQUIVALENCE",
            "scope_sha256": SCOPE,
            "evidence": {
                "authenticated_concept_binding": {
                    **receipt("EXACT_EQUIVALENT", "AUTHENTICATED_ONTOLOGY"),
                    "a_concept_id": "REGCAP:42",
                    "b_concept_id": "REGCAP:42",
                }
            },
        })
        self.assertTrue(out["pass"])
        self.assertIn("AUTHENTICATED_SHARED_CONCEPT_ID", out["proof_basis"])

    def test_mutual_entailment_proves_equivalence(self):
        out = prove({
            "expression_a": "A",
            "expression_b": "B",
            "required_relation": "BIDIRECTIONAL_EQUIVALENCE",
            "scope_sha256": SCOPE,
            "evidence": {
                "entailment_a_to_b": receipt("A_ENTAILS_B"),
                "entailment_b_to_a": receipt("B_ENTAILS_A"),
            },
        })
        self.assertTrue(out["pass"])
        self.assertIn("MUTUAL_VERIFIED_ENTAILMENT", out["proof_basis"])

    def test_one_way_entailment_does_not_get_upgraded_to_synonymy(self):
        out = prove({
            "expression_a": "CET1 capital",
            "expression_b": "regulatory capital",
            "required_relation": "BIDIRECTIONAL_EQUIVALENCE",
            "scope_sha256": SCOPE,
            "evidence": {"entailment_a_to_b": receipt("A_ENTAILS_B")},
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["strongest_proved_relation"], "A_ENTAILS_B")

    def test_directional_relation_can_be_sufficient(self):
        out = prove({
            "expression_a": "CET1 capital",
            "expression_b": "regulatory capital",
            "required_relation": "A_ENTAILS_B_REQUIRED",
            "scope_sha256": SCOPE,
            "evidence": {"entailment_a_to_b": receipt("A_ENTAILS_B")},
        })
        self.assertTrue(out["pass"])
        self.assertEqual(out["strongest_proved_relation"], "A_ENTAILS_B")

    def test_counterexample_kills_equivalence(self):
        out = prove({
            "expression_a": "reserve buffer",
            "expression_b": "liquidity cushion",
            "required_relation": "BIDIRECTIONAL_EQUIVALENCE",
            "scope_sha256": SCOPE,
            "evidence": {
                "entailment_a_to_b": receipt("A_ENTAILS_B"),
                "entailment_b_to_a": receipt("B_ENTAILS_A"),
                "counterexample_a_substituted_for_b": receipt("COUNTEREXAMPLE_A_FOR_B", "CHECKED_COUNTEREXAMPLE"),
            },
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "CONTRADICTORY_EQUIVALENCE_EVIDENCE")

    def test_task_equivalence_can_close_task_without_global_synonymy(self):
        out = prove({
            "expression_a": "reserve buffer",
            "expression_b": "liquidity cushion",
            "required_relation": "TASK_EQUIVALENCE",
            "scope_sha256": SCOPE,
            "evidence": {},
            "task_terminal_rows": terminal_rows(
                {"threshold": 10, "action": "REDUCE"},
                {"threshold": 10, "action": "REDUCE"},
            ),
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["strongest_proved_relation"], "TASK_EQUIVALENT")
        self.assertTrue(out["task_equivalent"])

    def test_different_terminal_signatures_do_not_get_merged(self):
        out = prove({
            "expression_a": "reserve buffer",
            "expression_b": "liquidity cushion",
            "required_relation": "TASK_EQUIVALENCE",
            "scope_sha256": SCOPE,
            "evidence": {},
            "task_terminal_rows": terminal_rows(
                {"action": "REDUCE"},
                {"action": "HOLD"},
            ),
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["strongest_proved_relation"], "UNKNOWN")

    def test_bare_verified_boolean_is_not_semantic_proof(self):
        out = prove({
            "expression_a": "A",
            "expression_b": "B",
            "required_relation": "BIDIRECTIONAL_EQUIVALENCE",
            "scope_sha256": SCOPE,
            "evidence": {"explicit_source_equivalence": {"verified": True}},
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["strongest_proved_relation"], "UNKNOWN")

    def test_scope_mismatch_cannot_promote_relation(self):
        out = prove({
            "expression_a": "A",
            "expression_b": "B",
            "required_relation": "BIDIRECTIONAL_EQUIVALENCE",
            "scope_sha256": SCOPE,
            "evidence": {
                "explicit_source_equivalence": receipt(
                    "EXACT_EQUIVALENT",
                    "EXPLICIT_SOURCE_DEFINITION",
                    scope="2" * 64,
                )
            },
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["strongest_proved_relation"], "UNKNOWN")

    def test_similarity_scores_are_never_authority(self):
        out = prove({
            "expression_a": "reserve buffer",
            "expression_b": "liquidity cushion",
            "required_relation": "ANY_SOUND_RELATION",
            "scope_sha256": SCOPE,
            "evidence": {"embedding_similarity": 0.99},
        })
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "UNSAFE_SIMILARITY_EVIDENCE_CANNOT_GRANT_SEMANTIC_RELATION",
        )

    def test_task_equivalence_does_not_upgrade_directional_relation_to_global_equivalence(self):
        out = prove({
            "expression_a": "A",
            "expression_b": "B",
            "required_relation": "TASK_EQUIVALENCE",
            "scope_sha256": SCOPE,
            "evidence": {"entailment_a_to_b": receipt("A_ENTAILS_B")},
            "task_terminal_rows": terminal_rows({"action": "X"}, {"action": "X"}),
        })
        self.assertTrue(out["pass"])
        self.assertEqual(out["strongest_proved_relation"], "A_ENTAILS_B")
        self.assertTrue(out["task_equivalent"])
        self.assertIn("ALSO_TASK_EQUIVALENT", out["proof_basis"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
