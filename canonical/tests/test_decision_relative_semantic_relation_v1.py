import unittest

from canonical.runtime.decision_relative_semantic_relation_v1 import prove


def receipt():
    return {"verified": True}


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
            "evidence": {"explicit_source_equivalence": receipt()},
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["strongest_proved_relation"], "EXACT_EQUIVALENT")

    def test_same_authenticated_concept_id_proves_exact_equivalence(self):
        out = prove({
            "expression_a": "reserve buffer",
            "expression_b": "liquidity cushion",
            "required_relation": "BIDIRECTIONAL_EQUIVALENCE",
            "evidence": {
                "authenticated_concept_binding": {
                    "verified": True,
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
            "evidence": {
                "entailment_a_to_b": receipt(),
                "entailment_b_to_a": receipt(),
            },
        })
        self.assertTrue(out["pass"])
        self.assertIn("MUTUAL_VERIFIED_ENTAILMENT", out["proof_basis"])

    def test_one_way_entailment_does_not_get_upgraded_to_synonymy(self):
        out = prove({
            "expression_a": "CET1 capital",
            "expression_b": "regulatory capital",
            "required_relation": "BIDIRECTIONAL_EQUIVALENCE",
            "evidence": {"entailment_a_to_b": receipt()},
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["strongest_proved_relation"], "A_ENTAILS_B")

    def test_directional_relation_can_be_sufficient(self):
        out = prove({
            "expression_a": "CET1 capital",
            "expression_b": "regulatory capital",
            "required_relation": "A_SUBSTITUTABLE_FOR_B",
            "evidence": {"entailment_a_to_b": receipt()},
        })
        self.assertTrue(out["pass"])
        self.assertEqual(out["strongest_proved_relation"], "A_ENTAILS_B")

    def test_counterexample_kills_equivalence(self):
        out = prove({
            "expression_a": "reserve buffer",
            "expression_b": "liquidity cushion",
            "required_relation": "BIDIRECTIONAL_EQUIVALENCE",
            "evidence": {
                "entailment_a_to_b": receipt(),
                "entailment_b_to_a": receipt(),
                "counterexample_a_substituted_for_b": receipt(),
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
            "evidence": {},
            "task_terminal_rows": terminal_rows(
                {"action": "REDUCE"},
                {"action": "HOLD"},
            ),
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["strongest_proved_relation"], "UNKNOWN")

    def test_similarity_scores_are_never_authority(self):
        out = prove({
            "expression_a": "reserve buffer",
            "expression_b": "liquidity cushion",
            "required_relation": "ANY_SOUND_RELATION",
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
            "evidence": {"entailment_a_to_b": receipt()},
            "task_terminal_rows": terminal_rows({"action": "X"}, {"action": "X"}),
        })
        self.assertTrue(out["pass"])
        self.assertEqual(out["strongest_proved_relation"], "A_ENTAILS_B")
        self.assertTrue(out["task_equivalent"])
        self.assertIn("ALSO_TASK_EQUIVALENT", out["proof_basis"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
