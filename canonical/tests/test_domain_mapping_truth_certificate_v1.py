import unittest

from canonical.runtime.domain_mapping_truth_certificate_v1 import (
    checked_predicate_id,
    evaluate,
)

RAW = "loss-absorbing cushion"
SCOPE = "finance:regulatory-capital:2026"


def candidate():
    return {
        "concept_id": "CCOB",
        "surface": "capital conservation buffer",
        "required_atoms": [],
        "forbidden_atoms": [],
    }


class Tests(unittest.TestCase):
    def test_explicit_definition_mints_authoritative_true_predicate(self):
        expected = checked_predicate_id(
            source_id="doc:A",
            raw_span=RAW,
            scope_id=SCOPE,
            target_concept_id="CCOB",
            required_relation="SEMANTIC_IDENTITY",
        )
        out = evaluate({
            "predicate_id": "caller-alias-is-not-authority",
            "raw_span": RAW,
            "source_id": "doc:A",
            "scope_id": SCOPE,
            "target_concept_id": "CCOB",
            "required_relation": "SEMANTIC_IDENTITY",
            "candidate_concepts": [candidate()],
            "relation_problems": {
                "CCOB": {
                    "required_relation": "SEMANTIC_IDENTITY",
                    "explicit_definition_sources": [{
                        "source_id": "doc:A",
                        "scope_id": SCOPE,
                        "source_text": (
                            "Loss-absorbing cushion means capital conservation buffer."
                        ),
                    }],
                }
            },
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_id"], expected)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertEqual(
            out["requested_predicate_id"],
            "caller-alias-is-not-authority",
        )
        self.assertFalse(out["requested_predicate_id_authority"])
        self.assertTrue(out["truthful_precommitment_observation"])
        self.assertFalse(out["terminal_authority"])

    def test_similarity_only_stays_unknown(self):
        out = evaluate({
            "predicate_id": "guess",
            "raw_span": RAW,
            "source_id": "doc:A",
            "scope_id": SCOPE,
            "target_concept_id": "CCOB",
            "required_relation": "SEMANTIC_IDENTITY",
            "candidate_concepts": [candidate()],
            "relation_problems": {
                "CCOB": {
                    "required_relation": "SEMANTIC_IDENTITY",
                    "candidate_relations": [{
                        "relation": "SIMILAR",
                        "score": 0.999,
                        "source": "embedding",
                    }],
                }
            },
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertFalse(out["truthful_precommitment_observation"])

    def test_scope_rebinding_fails_closed(self):
        out = evaluate({
            "predicate_id": "guess",
            "raw_span": RAW,
            "source_id": "doc:A",
            "scope_id": SCOPE,
            "target_concept_id": "CCOB",
            "required_relation": "SEMANTIC_IDENTITY",
            "candidate_concepts": [candidate()],
            "relation_problems": {
                "CCOB": {
                    "scope_id": "wrong",
                    "required_relation": "SEMANTIC_IDENTITY",
                }
            },
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["predicate_truth"], "UNKNOWN")

    def test_checked_predicate_identity_changes_with_scope_or_relation(self):
        a = checked_predicate_id(
            source_id="doc:A", raw_span=RAW, scope_id=SCOPE,
            target_concept_id="CCOB", required_relation="SEMANTIC_IDENTITY",
        )
        b = checked_predicate_id(
            source_id="doc:A", raw_span=RAW, scope_id=SCOPE + ":other",
            target_concept_id="CCOB", required_relation="SEMANTIC_IDENTITY",
        )
        c = checked_predicate_id(
            source_id="doc:A", raw_span=RAW, scope_id=SCOPE,
            target_concept_id="CCOB", required_relation="LEFT_ENTAILS_RIGHT",
        )
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, c)


    def test_unknown_mapping_exposes_minimum_proof_request(self):
        out = evaluate({
            "predicate_id": "guess",
            "raw_span": RAW,
            "source_id": "doc:A",
            "scope_id": SCOPE,
            "target_concept_id": "CCOB",
            "required_relation": "SEMANTIC_IDENTITY",
            "candidate_concepts": [candidate()],
            "relation_problems": {
                "CCOB": {
                    "required_relation": "SEMANTIC_IDENTITY",
                    "candidate_relations": [{
                        "relation": "SIMILAR",
                        "score": 0.999,
                        "source": "embedding",
                    }],
                }
            },
        })
        self.assertFalse(out["pass"])
        request = out["minimum_proof_request"]
        self.assertEqual(request["truth_kind"], "DOMAIN_MAPPING_RELATION")
        self.assertEqual(request["raw_span"], RAW)
        self.assertEqual(request["source_id"], "doc:A")
        self.assertEqual(request["scope_id"], SCOPE)
        self.assertEqual(request["target_concept_id"], "CCOB")
        self.assertEqual(request["required_relation"], "SEMANTIC_IDENTITY")
        self.assertIn(
            "AUTHENTICATED_SHARED_CONCEPT_IDENTITY",
            request["next_proof_targets"],
        )
        self.assertFalse(request["semantic_truth_authority"])
        self.assertFalse(request["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
