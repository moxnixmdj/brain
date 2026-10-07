import unittest

from canonical.runtime.certified_scope_fragment_v1 import parse_scope
from canonical.runtime.source_aligned_semantic_proof_v2 import verify_proof


class SourceAlignedSemanticProofV2Tests(unittest.TestCase):
    def _claim_from_parse(self, p):
        return {
            "claim_id": "scope",
            "kind": "SCOPE_RELATION",
            "scope_id": p["scope_id"],
            "relation": p["relation"],
            "operator_id": p["operator_id"],
            "left_role": p["left_role"],
            "left_span": p["left_span"],
            "right_role": p["right_role"],
            "right_span": p["right_span"],
        }

    def test_correct_unless_scope_is_proved(self):
        text = "Apply the rule unless the exception holds."
        parsed = parse_scope(text, source="s")["parse"]
        out = verify_proof(
            text,
            source_id="s",
            claims=[self._claim_from_parse(parsed)],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED")
        self.assertEqual(len(out["proved_constraints"]), 1)

    def test_swapped_scope_roles_are_rejected(self):
        text = "Apply the rule unless the exception holds."
        parsed = parse_scope(text, source="s")["parse"]
        claim = self._claim_from_parse(parsed)
        claim["left_role"], claim["right_role"] = claim["right_role"], claim["left_role"]
        out = verify_proof(text, source_id="s", claims=[claim])
        self.assertEqual(out["status"], "PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"], [])

    def test_wrong_scope_span_is_rejected(self):
        text = "Escalate if exposure exceeds the limit."
        parsed = parse_scope(text, source="s")["parse"]
        claim = self._claim_from_parse(parsed)
        claim["right_span"] = [0, 1]
        out = verify_proof(text, source_id="s", claims=[claim])
        self.assertEqual(out["proved_constraints"], [])

    def test_unresolved_multi_operator_source_cannot_mint_scope_fact(self):
        text = "Proceed if A, unless B."
        out = verify_proof(
            text,
            source_id="s",
            claims=[{
                "claim_id": "scope",
                "kind": "SCOPE_RELATION",
                "scope_id": "invented",
                "relation": "IF_THEN",
                "operator_id": "invented",
                "left_role": "ANTECEDENT",
                "left_span": [0, 1],
                "right_role": "CONSEQUENT",
                "right_span": [2, 3],
            }],
        )
        self.assertEqual(out["proved_constraints"], [])


if __name__ == "__main__":
    unittest.main()
