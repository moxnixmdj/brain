import hashlib
import json
import unittest

from canonical.runtime.semantic_relation_control_v1 import resolve


SCOPE = "finance:policy:2026"


def _sha(value):
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def terminal_signature_receipt(rows, *, scope=SCOPE, left_id=None, right_id=None):
    by_id = {row["raw_id"]: row for row in rows}
    ids = list(by_id)
    left_id = left_id or ids[0]
    right_id = right_id or ids[1]
    return {
        "pass": True,
        "schema": "PROJECT_BRAIN_TERMINAL_SIGNATURE_COMPLETENESS_AUTHORITY_RECEIPT_V1",
        "scope_id": scope,
        "left_id": left_id,
        "right_id": right_id,
        "left_terminal_signature_complete": True,
        "right_terminal_signature_complete": True,
        "left_terminal_signature_sha256": _sha(by_id[left_id]["terminal_signature"]),
        "right_terminal_signature_sha256": _sha(by_id[right_id]["terminal_signature"]),
        "verification_authority_mutated": False,
        "receipt_sha256": "f" * 64,
    }


def shared_concept_receipt(*, scope=SCOPE, left_id="A", right_id="B"):
    return {
        "pass": True,
        "schema": "PROJECT_BRAIN_SHARED_CONCEPT_IDENTITY_AUTHORITY_RECEIPT_V1",
        "scope_id": scope,
        "left_id": left_id,
        "right_id": right_id,
        "shared_concept_id": "REGCAP:42",
        "left_binding_authenticated": True,
        "right_binding_authenticated": True,
        "concept_semantics_authenticated": True,
        "left_binding_sha256": "a" * 64,
        "right_binding_sha256": "b" * 64,
        "registry_sha256": "c" * 64,
        "verification_authority_mutated": False,
        "receipt_sha256": "d" * 64,
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
        rows = [
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
        ]
        receipt = terminal_signature_receipt(rows, left_id="reserve-buffer", right_id="liquidity-cushion")
        out = resolve({
            "left_id": "reserve-buffer",
            "right_id": "liquidity-cushion",
            "scope_id": SCOPE,
            "required_relation": "CURRENT_DECISION_SUBSTITUTION",
            "terminal_signature_rows": rows,
            "terminal_signature_authority_receipt": receipt,
        }, terminal_signature_verifier=lambda value: value)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["strongest_proved_relation"],
            "CURRENT_DECISION_SUBSTITUTION",
        )
        self.assertFalse(out["proved_facts"]["semantic_identity"])

    def test_task_equivalence_does_not_prove_semantic_identity(self):
        rows = [
            {"raw_id": "A", "signature_complete": True, "terminal_signature": {"action": "ALLOW"}},
            {"raw_id": "B", "signature_complete": True, "terminal_signature": {"action": "ALLOW"}},
        ]
        out = resolve({
            "left_id": "A",
            "right_id": "B",
            "scope_id": SCOPE,
            "required_relation": "SEMANTIC_IDENTITY",
            "terminal_signature_rows": rows,
            "terminal_signature_authority_receipt": terminal_signature_receipt(rows),
        }, terminal_signature_verifier=lambda value: value)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["strongest_proved_relation"],
            "CURRENT_DECISION_SUBSTITUTION",
        )

    def test_terminal_difference_blocks_task_substitution(self):
        rows = [
            {"raw_id": "A", "signature_complete": True, "terminal_signature": {"action": "ALLOW"}},
            {"raw_id": "B", "signature_complete": True, "terminal_signature": {"action": "DENY"}},
        ]
        out = resolve({
            "left_id": "A",
            "right_id": "B",
            "scope_id": SCOPE,
            "required_relation": "CURRENT_DECISION_SUBSTITUTION",
            "terminal_signature_rows": rows,
            "terminal_signature_authority_receipt": terminal_signature_receipt(rows),
        }, terminal_signature_verifier=lambda value: value)
        self.assertFalse(out["pass"])
        self.assertFalse(out["proved_facts"]["current_decision_substitution"])

    def test_incomplete_terminal_signature_fails_to_prove_substitution(self):
        rows = [
            {"raw_id": "A", "signature_complete": False, "terminal_signature": {"action": "ALLOW"}},
            {"raw_id": "B", "signature_complete": True, "terminal_signature": {"action": "ALLOW"}},
        ]
        out = resolve({
            "left_id": "A",
            "right_id": "B",
            "scope_id": SCOPE,
            "required_relation": "CURRENT_DECISION_SUBSTITUTION",
            "terminal_signature_rows": rows,
            "terminal_signature_authority_receipt": terminal_signature_receipt(rows),
        }, terminal_signature_verifier=lambda value: value)
        self.assertFalse(out["pass"])
        self.assertIn(
            "SIGNATURE_COMPLETENESS_UNPROVED",
            out["terminal_equivalence"]["reason"],
        )

    def test_terminal_signature_rows_without_authority_receipt_fail_closed(self):
        rows = [
            {"raw_id": "A", "signature_complete": True, "terminal_signature": {"action": "ALLOW"}},
            {"raw_id": "B", "signature_complete": True, "terminal_signature": {"action": "ALLOW"}},
        ]
        out = resolve({
            "left_id": "A",
            "right_id": "B",
            "scope_id": SCOPE,
            "required_relation": "CURRENT_DECISION_SUBSTITUTION",
            "terminal_signature_rows": rows,
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED__TERMINAL_SIGNATURE_AUTHORITY_INVALID")
        self.assertEqual(out["reason"], "TERMINAL_SIGNATURE_AUTHORITY_RECEIPT_REQUIRED")

    def test_terminal_signature_authority_bound_to_wrong_signature_fails_closed(self):
        rows = [
            {"raw_id": "A", "signature_complete": True, "terminal_signature": {"action": "ALLOW"}},
            {"raw_id": "B", "signature_complete": True, "terminal_signature": {"action": "ALLOW"}},
        ]
        receipt = terminal_signature_receipt(rows)
        receipt["right_terminal_signature_sha256"] = "0" * 64
        out = resolve({
            "left_id": "A",
            "right_id": "B",
            "scope_id": SCOPE,
            "required_relation": "CURRENT_DECISION_SUBSTITUTION",
            "terminal_signature_rows": rows,
            "terminal_signature_authority_receipt": receipt,
        }, terminal_signature_verifier=lambda value: value)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED__TERMINAL_SIGNATURE_AUTHORITY_INVALID")
        self.assertIn("right_terminal_signature_sha256", out["terminal_equivalence"]["terminal_signature_authority"]["mismatch_fields"])

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

    def test_authenticated_shared_concept_identity_proves_semantic_identity(self):
        receipt = shared_concept_receipt()
        out = resolve(
            {
                "left_id": "A",
                "right_id": "B",
                "scope_id": SCOPE,
                "required_relation": "SEMANTIC_IDENTITY",
                "shared_concept_identity_receipt": receipt,
            },
            concept_identity_verifier=lambda value: value,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["strongest_proved_relation"], "SEMANTIC_IDENTITY")
        self.assertTrue(out["shared_concept_identity"]["proved"])
        self.assertEqual(
            out["shared_concept_identity"]["shared_concept_id"],
            "REGCAP:42",
        )

    def test_shared_concept_receipt_without_verifier_fails_closed(self):
        out = resolve({
            "left_id": "A",
            "right_id": "B",
            "scope_id": SCOPE,
            "required_relation": "SEMANTIC_IDENTITY",
            "shared_concept_identity_receipt": shared_concept_receipt(),
        })
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__SHARED_CONCEPT_IDENTITY_EVIDENCE_INVALID",
        )
        self.assertEqual(
            out["reason"],
            "SHARED_CONCEPT_IDENTITY_RECEIPT_AND_VERIFIER_REQUIRED",
        )

    def test_shared_concept_identity_wrong_scope_is_rejected(self):
        receipt = shared_concept_receipt(scope="another-scope")
        out = resolve(
            {
                "left_id": "A",
                "right_id": "B",
                "scope_id": SCOPE,
                "required_relation": "SEMANTIC_IDENTITY",
                "shared_concept_identity_receipt": receipt,
            },
            concept_identity_verifier=lambda value: value,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__SHARED_CONCEPT_IDENTITY_EVIDENCE_INVALID",
        )
        self.assertEqual(
            out["shared_concept_identity"]["reason"],
            "SHARED_CONCEPT_IDENTITY_BINDING_INVALID",
        )

    def test_shared_concept_identity_requires_content_address_bindings(self):
        receipt = shared_concept_receipt()
        receipt["registry_sha256"] = "not-a-digest"
        out = resolve(
            {
                "left_id": "A",
                "right_id": "B",
                "scope_id": SCOPE,
                "required_relation": "SEMANTIC_IDENTITY",
                "shared_concept_identity_receipt": receipt,
            },
            concept_identity_verifier=lambda value: value,
        )
        self.assertFalse(out["pass"])
        self.assertIn(
            "registry_sha256",
            out["shared_concept_identity"]["mismatch_fields"],
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
