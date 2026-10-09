import unittest

from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA,
    RECEIPT_SCHEMA,
    evidence_sha256,
    prove,
)


SCOPE = "finance:policy:2026"


def receipt(source, target, relation="ENTAILS", *, scope=SCOPE):
    return {
        "pass": True,
        "schema": RECEIPT_SCHEMA,
        "scope_id": scope,
        "source_id": source,
        "target_id": target,
        "relation": relation,
        "source_semantics_authenticated": True,
        "target_semantics_authenticated": True,
        "relation_semantics_authenticated": True,
        "verification_authority_mutated": False,
        "evidence_sha256": "a" * 64,
        "receipt_sha256": "b" * 64,
    }


def pack(edges=(), counters=(), left="A", right="B"):
    return {
        "schema": EVIDENCE_SCHEMA,
        "scope_id": SCOPE,
        "left_id": left,
        "right_id": right,
        "entailment_receipts": list(edges),
        "counterexample_receipts": list(counters),
    }


def run(e):
    return prove(
        e,
        expected_evidence_sha256=evidence_sha256(e),
        relation_verifier=lambda value: value,
    )


class Tests(unittest.TestCase):
    def test_direct_entailment(self):
        out = run(pack([receipt("A", "B")]))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["strongest_proved_relation"], "LEFT_ENTAILS_RIGHT")
        self.assertEqual(out["left_to_right_path"], ["A", "B"])

    def test_transitive_entailment_without_complete_universe(self):
        out = run(pack([receipt("A", "X"), receipt("X", "B")]))
        self.assertEqual(out["strongest_proved_relation"], "LEFT_ENTAILS_RIGHT")
        self.assertEqual(out["left_to_right_path"], ["A", "X", "B"])

    def test_mutual_paths_prove_scoped_logical_equivalence(self):
        out = run(pack([
            receipt("A", "X"),
            receipt("X", "B"),
            receipt("B", "Y"),
            receipt("Y", "A"),
        ]))
        self.assertEqual(out["strongest_proved_relation"], "LOGICAL_EQUIVALENCE_IN_SCOPE")
        self.assertTrue(out["logical_equivalence_in_scope"])

    def test_counterexample_disproves_direction(self):
        out = run(pack([], [receipt("A", "B", "NOT_ENTAILS")]))
        self.assertEqual(out["strongest_proved_relation"], "UNKNOWN")
        self.assertTrue(out["left_entails_right_disproved"])

    def test_counterexample_conflicting_with_transitive_path_fails_closed(self):
        out = run(pack(
            [receipt("A", "X"), receipt("X", "B")],
            [receipt("A", "B", "NOT_ENTAILS")],
        ))
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "CONTRADICTORY_ENTAILMENT_AND_COUNTEREXAMPLE_EVIDENCE",
        )

    def test_scope_mismatch_receipt_fails_closed(self):
        out = run(pack([receipt("A", "B", scope="wrong")]))
        self.assertFalse(out["pass"])
        self.assertIn("RELATION_RECEIPT_BINDING_INVALID", out["reason"])

    def test_missing_verifier_fails_closed(self):
        e = pack([receipt("A", "B")])
        out = prove(
            e,
            expected_evidence_sha256=evidence_sha256(e),
            relation_verifier=None,
        )
        self.assertFalse(out["pass"])
        self.assertIn("RELATION_RECEIPT_AND_VERIFIER_REQUIRED", out["reason"])

    def test_content_address_mismatch_fails_closed(self):
        e = pack([receipt("A", "B")])
        out = prove(
            e,
            expected_evidence_sha256="0" * 64,
            relation_verifier=lambda value: value,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EVIDENCE_CONTENT_ADDRESS_MISMATCH")


if __name__ == "__main__":
    unittest.main(verbosity=2)
