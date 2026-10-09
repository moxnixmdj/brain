import unittest

from canonical.runtime.bounded_semantic_relation_proof_v1 import (
    EVIDENCE_SCHEMA,
    evidence_sha256,
    prove,
)


def pack(left, right, universe=("a", "b", "c")):
    return {
        "schema": EVIDENCE_SCHEMA,
        "scope_id": "scope:test",
        "left_id": "L",
        "right_id": "R",
        "universe_complete": True,
        "left_extension_complete": True,
        "right_extension_complete": True,
        "universe": list(universe),
        "left_members": list(left),
        "right_members": list(right),
    }


def run(e):
    return prove(e, expected_evidence_sha256=evidence_sha256(e))


class Tests(unittest.TestCase):
    def test_equal_extensions_prove_scoped_logical_equivalence(self):
        out = run(pack(("a", "b"), ("a", "b")))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["strongest_proved_relation"], "LOGICAL_EQUIVALENCE_IN_SCOPE")
        self.assertTrue(out["left_entails_right"])
        self.assertTrue(out["right_entails_left"])
        self.assertFalse(out["logical_equivalence_disproved"])

    def test_left_subset_proves_only_left_entails_right(self):
        out = run(pack(("a",), ("a", "b")))
        self.assertEqual(out["strongest_proved_relation"], "LEFT_ENTAILS_RIGHT")
        self.assertTrue(out["left_entails_right"])
        self.assertFalse(out["right_entails_left"])
        self.assertEqual(out["right_not_left_witnesses"], ["b"])

    def test_right_subset_proves_only_right_entails_left(self):
        out = run(pack(("a", "b"), ("a",)))
        self.assertEqual(out["strongest_proved_relation"], "RIGHT_ENTAILS_LEFT")
        self.assertFalse(out["left_entails_right"])
        self.assertTrue(out["right_entails_left"])
        self.assertEqual(out["left_not_right_witnesses"], ["b"])

    def test_partial_overlap_produces_counterexamples_both_directions(self):
        out = run(pack(("a", "b"), ("b", "c")))
        self.assertEqual(out["strongest_proved_relation"], "PARTIAL_OVERLAP_OR_INCOMPARABLE")
        self.assertEqual(out["left_not_right_witnesses"], ["a"])
        self.assertEqual(out["right_not_left_witnesses"], ["c"])
        self.assertTrue(out["logical_equivalence_disproved"])

    def test_disjoint_sets_are_not_mislabeled_synonyms(self):
        out = run(pack(("a",), ("b",)))
        self.assertEqual(out["strongest_proved_relation"], "DISJOINT")
        self.assertTrue(out["logical_equivalence_disproved"])

    def test_digest_mismatch_fails_closed(self):
        e = pack(("a",), ("a",))
        out = prove(e, expected_evidence_sha256="0" * 64)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EVIDENCE_CONTENT_ADDRESS_MISMATCH")

    def test_incomplete_extension_cannot_prove_relation(self):
        e = pack(("a",), ("a",))
        e["left_extension_complete"] = False
        out = run(e)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "LEFT_EXTENSION_COMPLETENESS_UNPROVED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
