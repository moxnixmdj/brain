import hashlib
import unittest

from canonical.runtime.semantic_operator_counterfactuals import extract_semantic_operators
from canonical.runtime.source_aligned_semantic_proof_v1 import verify_proof


class SourceAlignedSemanticProofTests(unittest.TestCase):
    def test_correct_operator_class_is_proved(self):
        text = "Apply the rule unless the exception holds."
        op = extract_semantic_operators(text, source="s")[0]
        self.assertEqual(op.semantic_class, "CONDITIONAL_UNLESS")
        out = verify_proof(
            text,
            source_id="s",
            claims=[{
                "claim_id": "c1",
                "kind": "OPERATOR_CLASS",
                "operator_id": op.operator_id,
                "semantic_class": "CONDITIONAL_UNLESS",
            }],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED")
        self.assertEqual(len(out["proved_constraints"]), 1)

    def test_wrong_operator_class_is_rejected(self):
        text = "Apply the rule unless the exception holds."
        op = extract_semantic_operators(text, source="s")[0]
        out = verify_proof(
            text,
            source_id="s",
            claims=[{
                "claim_id": "c1",
                "kind": "OPERATOR_CLASS",
                "operator_id": op.operator_id,
                "semantic_class": "CONDITIONAL_IF",
            }],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"], [])

    def test_numeric_bound_is_recomputed(self):
        text = "Exposure must be at least 3."
        op = next(x for x in extract_semantic_operators(text, source="s") if x.semantic_class == "MIN_INCLUSIVE")
        good = verify_proof(
            text,
            source_id="s",
            claims=[{
                "claim_id": "good",
                "kind": "OPERATOR_BOUND",
                "operator_id": op.operator_id,
                "semantic_class": "MIN_INCLUSIVE",
                "bound_value": 3,
            }],
        )
        bad = verify_proof(
            text,
            source_id="s",
            claims=[{
                "claim_id": "bad",
                "kind": "OPERATOR_BOUND",
                "operator_id": op.operator_id,
                "semantic_class": "MIN_INCLUSIVE",
                "bound_value": 4,
            }],
        )
        self.assertEqual(good["status"], "PROOF_CHECKED")
        self.assertEqual(bad["proved_constraints"], [])

    def test_literal_proof_checks_exact_span_hash(self):
        text = "ABC applies."
        digest = hashlib.sha256(b"ABC").hexdigest()
        out = verify_proof(
            text,
            source_id="s",
            claims=[{
                "claim_id": "literal",
                "kind": "SOURCE_LITERAL",
                "start": 0,
                "end": 3,
                "text_sha256": digest,
            }],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED")
        self.assertEqual(out["accepted_claims"][0]["source_text"], "ABC")

    def test_unproved_high_level_meaning_is_not_supported(self):
        out = verify_proof(
            "The transaction qualifies.",
            source_id="s",
            claims=[{
                "claim_id": "guess",
                "kind": "SEMANTIC_MEANING",
                "meaning": "EXCEPTION_C_APPLIES",
            }],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"], [])


if __name__ == "__main__":
    unittest.main()
