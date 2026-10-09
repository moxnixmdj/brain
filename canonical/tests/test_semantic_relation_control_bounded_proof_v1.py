import unittest

from canonical.runtime.bounded_semantic_relation_proof_v1 import (
    EVIDENCE_SCHEMA,
    evidence_sha256,
)
from canonical.runtime.semantic_relation_control_v1 import resolve


SCOPE = "finance:policy:2026"


def evidence(left, right, universe=("a", "b", "c")):
    return {
        "schema": EVIDENCE_SCHEMA,
        "scope_id": SCOPE,
        "left_id": "L",
        "right_id": "R",
        "universe_complete": True,
        "left_extension_complete": True,
        "right_extension_complete": True,
        "universe": list(universe),
        "left_members": list(left),
        "right_members": list(right),
    }


def problem(required, e):
    return {
        "left_id": "L",
        "right_id": "R",
        "left_surface": "reserve buffer",
        "right_surface": "liquidity cushion",
        "scope_id": SCOPE,
        "required_relation": required,
        "bounded_extension_evidence": e,
        "expected_bounded_extension_sha256": evidence_sha256(e),
    }


class Tests(unittest.TestCase):
    def test_extensional_equality_proves_scoped_equivalence_not_identity(self):
        e = evidence(("a", "b"), ("a", "b"))
        out = resolve(problem("LOGICAL_EQUIVALENCE_IN_SCOPE", e))
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["strongest_proved_relation"],
            "LOGICAL_EQUIVALENCE_IN_SCOPE",
        )
        self.assertFalse(out["proved_facts"]["semantic_identity"])
        self.assertTrue(out["proved_facts"]["left_entails_right"])
        self.assertTrue(out["proved_facts"]["right_entails_left"])

    def test_left_subset_proves_directional_entailment_without_synonymy(self):
        e = evidence(("a",), ("a", "b"))
        out = resolve(problem("LEFT_ENTAILS_RIGHT", e))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["strongest_proved_relation"], "LEFT_ENTAILS_RIGHT")
        self.assertFalse(out["proved_facts"]["right_entails_left"])
        self.assertFalse(out["proved_facts"]["semantic_identity"])

    def test_incomparability_disproves_equivalence_and_stops_synonym_search(self):
        e = evidence(("a", "b"), ("b", "c"))
        out = resolve(problem("LOGICAL_EQUIVALENCE_IN_SCOPE", e))
        self.assertFalse(out["pass"])
        self.assertTrue(out["required_relation_disproved"])
        self.assertEqual(
            out["status"],
            "PROVED__REQUIRED_SEMANTIC_RELATION_FALSE_IN_BOUND_SCOPE",
        )
        self.assertEqual(out["next_proof_targets"], [])
        self.assertEqual(
            out["action"],
            "PRESERVE_DISTINCT_MEANINGS__COUNTEREXAMPLE_BOUND",
        )
        proof = out["bounded_extension_proof"]
        self.assertEqual(proof["left_not_right_witnesses"], ["a"])
        self.assertEqual(proof["right_not_left_witnesses"], ["c"])

    def test_right_entailment_counterexample_is_decisive(self):
        e = evidence(("a", "b"), ("a",))
        out = resolve(problem("LEFT_ENTAILS_RIGHT", e))
        self.assertFalse(out["pass"])
        self.assertTrue(out["required_relation_disproved"])
        self.assertEqual(
            out["bounded_extension_proof"]["left_not_right_witnesses"],
            ["b"],
        )

    def test_bad_content_address_fails_closed(self):
        e = evidence(("a",), ("a",))
        p = problem("LOGICAL_EQUIVALENCE_IN_SCOPE", e)
        p["expected_bounded_extension_sha256"] = "0" * 64
        out = resolve(p)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__BOUNDED_EXTENSION_EVIDENCE_INVALID",
        )

    def test_scope_binding_mismatch_fails_closed(self):
        e = evidence(("a",), ("a",))
        e["scope_id"] = "other:scope"
        p = {
            "left_id": "L",
            "right_id": "R",
            "scope_id": SCOPE,
            "required_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
            "bounded_extension_evidence": e,
            "expected_bounded_extension_sha256": evidence_sha256(e),
        }
        out = resolve(p)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__BOUNDED_EXTENSION_BINDING_MISMATCH",
        )

    def test_candidate_similarity_cannot_override_proved_counterexample(self):
        e = evidence(("a",), ("b",))
        p = problem("LOGICAL_EQUIVALENCE_IN_SCOPE", e)
        p["candidate_relations"] = [
            {"relation": "SIMILAR", "score": 0.9999, "source": "embedding"}
        ]
        out = resolve(p)
        self.assertFalse(out["pass"])
        self.assertTrue(out["required_relation_disproved"])
        self.assertFalse(out["candidate_relations_are_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
