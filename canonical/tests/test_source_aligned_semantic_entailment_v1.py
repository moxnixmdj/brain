import hashlib
import unittest

from canonical.runtime.source_aligned_semantic_entailment_v1 import prove


SCOPE = "finance:policy:2026"


def span(source_id, text, scope=SCOPE):
    return {
        "source_id": source_id,
        "scope_id": scope,
        "span_text": text,
        "span_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


class Tests(unittest.TestCase):
    def test_direct_inclusion_proves_one_way_entailment(self):
        out = prove({
            "left_surface": "CET1 capital",
            "right_surface": "regulatory capital",
            "scope_id": SCOPE,
            "required_relation": "LEFT_ENTAILS_RIGHT",
            "source_spans": [
                span("doc:A", "CET1 capital is a type of regulatory capital.")
            ],
        })
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["proved_facts"]["left_entails_right"])
        self.assertFalse(out["proved_facts"]["right_entails_left"])

    def test_transitive_cross_source_chain_is_checked(self):
        out = prove({
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "LEFT_ENTAILS_RIGHT",
            "source_spans": [
                span("doc:A", "Every reserve buffer is a liquidity reserve."),
                span("doc:B", "Every liquidity reserve is a liquidity cushion."),
            ],
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(len(out["left_to_right_proof_atom_ids"]), 2)

    def test_mutual_checked_chains_prove_logical_equivalence_not_identity(self):
        out = prove({
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
            "source_spans": [
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

    def test_exact_definition_is_bidirectional(self):
        out = prove({
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
            "source_spans": [
                span("doc:A", "Reserve buffer means liquidity cushion.")
            ],
        })
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["proved_facts"]["logical_equivalence_in_scope"])

    def test_one_way_relation_is_not_upgraded_to_equivalence(self):
        out = prove({
            "left_surface": "CET1 capital",
            "right_surface": "regulatory capital",
            "scope_id": SCOPE,
            "required_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
            "source_spans": [
                span("doc:A", "CET1 capital is a type of regulatory capital.")
            ],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["strongest_proved_relation"], "LEFT_ENTAILS_RIGHT")

    def test_exact_counterexample_disproves_direction(self):
        out = prove({
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "ANY_DIRECTIONAL_RELATION",
            "source_spans": [
                span("doc:A", "Some reserve buffer is not a liquidity cushion.")
            ],
        })
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["proved_facts"]["left_entails_right_disproved"])

    def test_proof_counterexample_conflict_fails_closed(self):
        out = prove({
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "LEFT_ENTAILS_RIGHT",
            "source_spans": [
                span("doc:A", "Every reserve buffer is a liquidity cushion."),
                span("doc:B", "Some reserve buffer is not a liquidity cushion."),
            ],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__SEMANTIC_RELATION_EVIDENCE_CONFLICT",
        )

    def test_scope_mismatch_fails_closed(self):
        out = prove({
            "left_surface": "A",
            "right_surface": "B",
            "scope_id": SCOPE,
            "required_relation": "LEFT_ENTAILS_RIGHT",
            "source_spans": [span("doc:A", "Every A is B.", scope="other")],
        })
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_SCOPE_MISMATCH", out["reason"])

    def test_content_hash_mismatch_fails_closed(self):
        row = span("doc:A", "Every A is B.")
        row["span_sha256"] = "0" * 64
        out = prove({
            "left_surface": "A",
            "right_surface": "B",
            "scope_id": SCOPE,
            "required_relation": "LEFT_ENTAILS_RIGHT",
            "source_spans": [row],
        })
        self.assertFalse(out["pass"])
        self.assertIn("SHA256_MISMATCH", out["reason"])

    def test_unsupported_relation_span_fails_closed_instead_of_guessing(self):
        out = prove({
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "LEFT_ENTAILS_RIGHT",
            "source_spans": [
                span("doc:A", "Reserve buffers resemble liquidity cushions.")
            ],
        })
        self.assertFalse(out["pass"])
        self.assertIn("OUTSIDE_CHECKED_RELATION_GRAMMAR", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
