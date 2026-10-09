import hashlib
import unittest

from canonical.runtime.semantic_relation_control_v1 import resolve


SCOPE = "finance:policy:2026"


def span(source_id, text, scope=SCOPE):
    return {
        "source_id": source_id,
        "scope_id": scope,
        "span_text": text,
        "span_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


class Tests(unittest.TestCase):
    def test_similarity_candidate_never_certifies_equivalence(self):
        out = resolve({
            "left_id": "reserve-buffer",
            "right_id": "liquidity-cushion",
            "scope_id": SCOPE,
            "required_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
            "candidate_relations": [
                {"relation": "SIMILAR", "score": 0.99, "source": "embedding"}
            ],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["strongest_proved_relation"], "UNKNOWN")
        self.assertFalse(out["candidate_relations_are_authority"])

    def test_exact_source_definition_proves_scoped_identity(self):
        out = resolve({
            "left_id": "reserve-buffer",
            "right_id": "liquidity-cushion",
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "SEMANTIC_IDENTITY",
            "explicit_definition_sources": [{
                "source_id": "doc:A",
                "scope_id": SCOPE,
                "source_text": "Reserve buffer means liquidity cushion.",
            }],
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["strongest_proved_relation"], "SEMANTIC_IDENTITY")
        self.assertFalse(out["scope_leakage_authorized"])

    def test_reverse_exact_source_definition_also_proves_scoped_identity(self):
        out = resolve({
            "left_id": "reserve-buffer",
            "right_id": "liquidity-cushion",
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "SEMANTIC_IDENTITY",
            "explicit_definition_sources": [{
                "source_id": "doc:A",
                "scope_id": SCOPE,
                "source_text": "Liquidity cushion is defined as reserve buffer.",
            }],
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["strongest_proved_relation"], "SEMANTIC_IDENTITY")

    def test_nonexplicit_paraphrase_stays_unknown_and_gets_precise_proof_targets(self):
        out = resolve({
            "left_id": "reserve-buffer",
            "right_id": "liquidity-cushion",
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
            "explicit_definition_sources": [{
                "source_id": "doc:A",
                "scope_id": SCOPE,
                "source_text": "The reserve buffer remains large. The liquidity cushion is reviewed monthly.",
            }],
            "candidate_relations": [
                {"relation": "SIMILAR", "source": "lexical-model"}
            ],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["strongest_proved_relation"], "UNKNOWN")
        self.assertEqual(
            out["next_proof_targets"][:2],
            [
                "SOURCE_ALIGNED_LEFT_TO_RIGHT_ENTAILMENT_PROOF",
                "SOURCE_ALIGNED_RIGHT_TO_LEFT_ENTAILMENT_PROOF",
            ],
        )

    def test_complete_terminal_signature_equality_is_enough_for_current_decision(self):
        out = resolve({
            "left_id": "reserve-buffer",
            "right_id": "liquidity-cushion",
            "scope_id": SCOPE,
            "required_relation": "CURRENT_DECISION_SUBSTITUTION",
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

    def test_incomplete_terminal_signature_fails_to_prove_substitution(self):
        out = resolve({
            "left_id": "A",
            "right_id": "B",
            "scope_id": SCOPE,
            "required_relation": "CURRENT_DECISION_SUBSTITUTION",
            "terminal_signature_rows": [
                {
                    "raw_id": "A",
                    "signature_complete": False,
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
        self.assertIn(
            "SIGNATURE_COMPLETENESS_UNPROVED",
            out["terminal_equivalence"]["reason"],
        )

    def test_conflicting_explicit_definitions_fail_closed(self):
        out = resolve({
            "left_id": "reserve-buffer",
            "right_id": "liquidity-cushion",
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "SEMANTIC_IDENTITY",
            "explicit_definition_sources": [{
                "source_id": "doc:A",
                "scope_id": SCOPE,
                "source_text": (
                    "Reserve buffer means liquidity cushion. "
                    "Reserve buffer means capital reserve."
                ),
            }],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__EXPLICIT_SOURCE_EVIDENCE_INVALID",
        )

    def test_wrong_scope_source_is_rejected_not_reused(self):
        out = resolve({
            "left_id": "A",
            "right_id": "B",
            "scope_id": SCOPE,
            "required_relation": "SEMANTIC_IDENTITY",
            "explicit_definition_sources": [{
                "source_id": "doc:A",
                "scope_id": "another-scope",
                "source_text": "A means B.",
            }],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__EXPLICIT_SOURCE_EVIDENCE_INVALID",
        )


    def test_checked_cross_source_chain_proves_directional_relation(self):
        out = resolve({
            "left_id": "reserve-buffer",
            "right_id": "liquidity-cushion",
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "LEFT_ENTAILS_RIGHT",
            "source_entailment_spans": [
                span("doc:A", "Every reserve buffer is a liquidity reserve."),
                span("doc:B", "Every liquidity reserve is a liquidity cushion."),
            ],
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["strongest_proved_relation"],
            "LEFT_ENTAILS_RIGHT",
        )
        self.assertTrue(out["proved_facts"]["left_entails_right"])
        self.assertFalse(out["proved_facts"]["right_entails_left"])

    def test_mutual_checked_entailment_proves_logical_equivalence_not_identity(self):
        out = resolve({
            "left_id": "reserve-buffer",
            "right_id": "liquidity-cushion",
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
            "source_entailment_spans": [
                span("doc:A", "Every reserve buffer is a liquidity reserve."),
                span("doc:B", "Every liquidity reserve is a liquidity cushion."),
                span("doc:C", "Every liquidity cushion is a reserve buffer."),
            ],
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["strongest_proved_relation"],
            "LOGICAL_EQUIVALENCE_IN_SCOPE",
        )
        self.assertFalse(out["proved_facts"]["semantic_identity"])

    def test_counterexample_conflict_in_source_entailment_fails_closed(self):
        out = resolve({
            "left_id": "reserve-buffer",
            "right_id": "liquidity-cushion",
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "LEFT_ENTAILS_RIGHT",
            "source_entailment_spans": [
                span("doc:A", "Every reserve buffer is a liquidity cushion."),
                span("doc:B", "Some reserve buffer is not a liquidity cushion."),
            ],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__SOURCE_ALIGNED_ENTAILMENT_INVALID",
        )

    def test_generic_proof_record_field_is_rejected(self):
        out = resolve({
            "left_id": "A",
            "right_id": "B",
            "scope_id": SCOPE,
            "required_relation": "SEMANTIC_IDENTITY",
            "proof_records": [{"verified": True}],
        })
        self.assertFalse(out["pass"])
        self.assertIn("UNMODELED_FIELDS:proof_records", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
