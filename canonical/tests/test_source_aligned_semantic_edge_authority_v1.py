from __future__ import annotations

from hashlib import sha256
import json
import unittest

from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA,
    evidence_sha256,
    prove as prove_dag,
)
from canonical.runtime.source_aligned_semantic_edge_authority_v1 import (
    CONCEPT_SEMANTICS_RECEIPT_SCHEMA,
    SOURCE_COMPLETENESS_RECEIPT_SCHEMA,
    prove,
)


RAW = "loss-absorbing cushion"
SOURCE = "doc:A"
SCOPE = "finance:regulatory-capital:2026"
TARGET = "CCOB"


def canon_sha(value):
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def atom(name):
    return {"op": "ATOM", "id": name}


def conj(*rows):
    return {"op": "AND", "args": list(rows)}


def source_verifier(constraints):
    def verify(
        _raw_span,
        *,
        source_id,
        claims,
        typed_context=None,
        expected_typed_context_sha256=None,
        fact_source=None,
        fact_source_id=None,
    ):
        return {
            "status": "PROOF_CHECKED",
            "source_id": source_id,
            "accepted_claims": list(claims),
            "rejected_claims": [],
            "proved_constraints": list(constraints),
            "terminal_authority": False,
        }

    return verify


def concept_verifier(formula, *, target=TARGET, scope=SCOPE):
    def verify(_receipt):
        return {
            "pass": True,
            "schema": CONCEPT_SEMANTICS_RECEIPT_SCHEMA,
            "scope_id": scope,
            "concept_id": target,
            "formula_sha256": canon_sha(formula),
            "definition_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
            "concept_semantics_authenticated": True,
            "formula_semantics_authenticated": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "a" * 64,
        }

    return verify


def completeness_verifier(constraints, *, raw=RAW, source=SOURCE, scope=SCOPE):
    def verify(_receipt):
        return {
            "pass": True,
            "schema": SOURCE_COMPLETENESS_RECEIPT_SCHEMA,
            "source_id": source,
            "scope_id": scope,
            "raw_span_sha256": sha256(raw.encode("utf-8")).hexdigest(),
            "proved_constraints_sha256": canon_sha(list(constraints)),
            "decision_relevant_semantics_complete": True,
            "source_constraints_semantics_authenticated": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "b" * 64,
        }

    return verify


class Tests(unittest.TestCase):
    def test_partial_source_semantics_can_prove_source_to_target(self):
        formula = atom("LOSS_ABSORPTION")
        out = prove(
            RAW,
            source_id=SOURCE,
            scope_id=SCOPE,
            target_concept_id=TARGET,
            direction="SOURCE_TO_TARGET",
            source_claims=[],
            target_formula=formula,
            concept_semantics_receipt={"candidate": True},
            concept_semantics_verifier=concept_verifier(formula),
            source_proof_verifier=source_verifier([atom("LOSS_ABSORPTION")]),
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_edge_authority"])
        self.assertIsNone(out["source_completeness_authority"])
        self.assertEqual(out["edge_receipt"]["relation"], "ENTAILS")
        self.assertTrue(out["edge_receipt"]["source_id"].startswith("MENTION:"))
        self.assertEqual(out["edge_receipt"]["target_id"], TARGET)

    def test_missing_source_fact_keeps_forward_entailment_unknown(self):
        formula = conj(atom("LOSS_ABSORPTION"), atom("GOING_CONCERN"))
        out = prove(
            RAW,
            source_id=SOURCE,
            scope_id=SCOPE,
            target_concept_id=TARGET,
            direction="SOURCE_TO_TARGET",
            source_claims=[],
            target_formula=formula,
            concept_semantics_receipt={"candidate": True},
            concept_semantics_verifier=concept_verifier(formula),
            source_proof_verifier=source_verifier([atom("LOSS_ABSORPTION")]),
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "UNKNOWN__ENTAILMENT_NOT_PROVED")
        self.assertFalse(out["nonentailment_authority"])
        self.assertIsNone(out["edge_receipt"])

    def test_unverified_claim_cannot_supply_missing_fact(self):
        formula = conj(atom("LOSS_ABSORPTION"), atom("GOING_CONCERN"))
        out = prove(
            RAW,
            source_id=SOURCE,
            scope_id=SCOPE,
            target_concept_id=TARGET,
            direction="SOURCE_TO_TARGET",
            source_claims=[{
                "claim_id": "guess",
                "kind": "MODEL_GUESS",
                "semantic_atom": "GOING_CONCERN",
            }],
            target_formula=formula,
            concept_semantics_receipt={"candidate": True},
            concept_semantics_verifier=concept_verifier(formula),
            source_proof_verifier=source_verifier([atom("LOSS_ABSORPTION")]),
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "UNKNOWN__ENTAILMENT_NOT_PROVED")

    def test_concept_formula_mismatch_fails_closed(self):
        formula = atom("LOSS_ABSORPTION")

        def wrong(_receipt):
            result = concept_verifier(atom("OTHER"))(_receipt)
            return result

        out = prove(
            RAW,
            source_id=SOURCE,
            scope_id=SCOPE,
            target_concept_id=TARGET,
            direction="SOURCE_TO_TARGET",
            source_claims=[],
            target_formula=formula,
            concept_semantics_receipt={"candidate": True},
            concept_semantics_verifier=wrong,
            source_proof_verifier=source_verifier([atom("LOSS_ABSORPTION")]),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CONCEPT_SEMANTICS_RECEIPT_BINDING_INVALID", out["reason"])

    def test_reverse_entailment_requires_source_completeness(self):
        formula = conj(atom("LOSS_ABSORPTION"), atom("GOING_CONCERN"))
        out = prove(
            RAW,
            source_id=SOURCE,
            scope_id=SCOPE,
            target_concept_id=TARGET,
            direction="TARGET_TO_SOURCE",
            source_claims=[],
            target_formula=formula,
            concept_semantics_receipt={"candidate": True},
            concept_semantics_verifier=concept_verifier(formula),
            source_proof_verifier=source_verifier([atom("LOSS_ABSORPTION")]),
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "UNKNOWN__SOURCE_SEMANTICS_COMPLETENESS_REQUIRED",
        )
        self.assertIsNone(out["edge_receipt"])

    def test_reverse_entailment_passes_only_with_bound_completeness(self):
        constraints = [atom("LOSS_ABSORPTION")]
        formula = conj(atom("LOSS_ABSORPTION"), atom("GOING_CONCERN"))
        out = prove(
            RAW,
            source_id=SOURCE,
            scope_id=SCOPE,
            target_concept_id=TARGET,
            direction="TARGET_TO_SOURCE",
            source_claims=[],
            target_formula=formula,
            concept_semantics_receipt={"candidate": True},
            concept_semantics_verifier=concept_verifier(formula),
            source_completeness_receipt={"candidate": True},
            source_completeness_verifier=completeness_verifier(constraints),
            source_proof_verifier=source_verifier(constraints),
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["edge_receipt"]["source_id"], TARGET)
        self.assertTrue(out["edge_receipt"]["target_id"].startswith("MENTION:"))

    def test_reverse_failure_is_unknown_not_not_entails(self):
        constraints = [atom("LOSS_ABSORPTION"), atom("GOING_CONCERN")]
        formula = atom("LOSS_ABSORPTION")
        out = prove(
            RAW,
            source_id=SOURCE,
            scope_id=SCOPE,
            target_concept_id=TARGET,
            direction="TARGET_TO_SOURCE",
            source_claims=[],
            target_formula=formula,
            concept_semantics_receipt={"candidate": True},
            concept_semantics_verifier=concept_verifier(formula),
            source_completeness_receipt={"candidate": True},
            source_completeness_verifier=completeness_verifier(constraints),
            source_proof_verifier=source_verifier(constraints),
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "UNKNOWN__ENTAILMENT_NOT_PROVED")
        self.assertFalse(out["nonentailment_authority"])

    def test_edge_receipt_is_accepted_by_existing_entailment_dag(self):
        formula = atom("LOSS_ABSORPTION")
        out = prove(
            RAW,
            source_id=SOURCE,
            scope_id=SCOPE,
            target_concept_id=TARGET,
            direction="SOURCE_TO_TARGET",
            source_claims=[],
            target_formula=formula,
            concept_semantics_receipt={"candidate": True},
            concept_semantics_verifier=concept_verifier(formula),
            source_proof_verifier=source_verifier([atom("LOSS_ABSORPTION")]),
        )
        self.assertTrue(out["pass"], out)
        receipt = out["edge_receipt"]
        evidence = {
            "schema": EVIDENCE_SCHEMA,
            "scope_id": SCOPE,
            "left_id": receipt["source_id"],
            "right_id": receipt["target_id"],
            "entailment_receipts": [receipt],
            "counterexample_receipts": [],
        }
        dag = prove_dag(
            evidence,
            expected_evidence_sha256=evidence_sha256(evidence),
            relation_verifier=lambda value: value,
        )
        self.assertTrue(dag["pass"], dag)
        self.assertTrue(dag["left_entails_right"])

    def test_default_v8_source_checker_can_supply_real_source_literal_constraint(self):
        raw = "ABC"
        digest = sha256(raw.encode("utf-8")).hexdigest()
        constraint_id = f"SOURCE_LITERAL::literal-doc::0:3::{digest}"
        formula = atom(constraint_id)
        out = prove(
            raw,
            source_id="literal-doc",
            scope_id=SCOPE,
            target_concept_id="LITERAL_DEFINED_CONCEPT",
            direction="SOURCE_TO_TARGET",
            source_claims=[{
                "claim_id": "literal",
                "kind": "SOURCE_LITERAL",
                "start": 0,
                "end": 3,
                "text_sha256": digest,
            }],
            target_formula=formula,
            concept_semantics_receipt={"candidate": True},
            concept_semantics_verifier=concept_verifier(
                formula,
                target="LITERAL_DEFINED_CONCEPT",
            ),
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["proved_constraints"],
            [{"op": "ATOM", "id": constraint_id}],
        )

    def test_no_terminal_or_acceptance_authority(self):
        formula = atom("LOSS_ABSORPTION")
        out = prove(
            RAW,
            source_id=SOURCE,
            scope_id=SCOPE,
            target_concept_id=TARGET,
            direction="SOURCE_TO_TARGET",
            source_claims=[],
            target_formula=formula,
            concept_semantics_receipt={"candidate": True},
            concept_semantics_verifier=concept_verifier(formula),
            source_proof_verifier=source_verifier([atom("LOSS_ABSORPTION")]),
        )
        self.assertTrue(out["pass"])
        self.assertFalse(out["terminal_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
