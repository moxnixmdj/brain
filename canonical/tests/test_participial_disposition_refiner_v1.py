from __future__ import annotations

from hashlib import sha256
import json
import unittest

from canonical.runtime.bounded_participial_disposition_v1 import (
    SEMANTIC_ATOM,
    verify_span,
)
from canonical.runtime.source_aligned_participial_disposition_proof_v1 import verify_proof
from canonical.runtime.source_aligned_semantic_edge_authority_v1 import (
    CONCEPT_SEMANTICS_RECEIPT_SCHEMA,
    prove,
)

RAW = "loss-absorbing cushion"
SOURCE = "doc:A"
SCOPE = "finance:regulatory-capital:2026"


def atom(name):
    return {"op": "ATOM", "id": name}


def conj(*rows):
    return {"op": "AND", "args": list(rows)}


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


def concept_verifier(formula, concept_id):
    def verify(_receipt):
        return {
            "pass": True,
            "schema": CONCEPT_SEMANTICS_RECEIPT_SCHEMA,
            "scope_id": SCOPE,
            "concept_id": concept_id,
            "formula_sha256": canon_sha(formula),
            "definition_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
            "concept_semantics_authenticated": True,
            "formula_semantics_authenticated": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "a" * 64,
        }

    return verify


class ParticipialDispositionTests(unittest.TestCase):
    def test_exact_phrase_proves_only_dispositional_loss_absorption(self):
        out = verify_span(RAW, start=0, end=len(RAW))
        self.assertEqual(out["status"], "PROVED", out)
        self.assertEqual(
            out["semantic_graph"],
            {
                "head": "cushion",
                "predicate": "absorb",
                "object": "loss",
                "reading": "DISPOSITIONAL",
            },
        )
        self.assertEqual(
            out["proved_constraint"],
            {"op": "ATOM", "id": SEMANTIC_ATOM},
        )
        self.assertFalse(out["episodic_current_event_claimed"])
        self.assertFalse(out["concept_identity_claimed"])

    def test_space_without_hyphen_is_unresolved(self):
        text = "loss absorbing cushion"
        out = verify_span(text, start=0, end=len(text))
        self.assertEqual(out["status"], "UNRESOLVED")

    def test_passive_participle_is_unresolved(self):
        text = "loss-absorbed cushion"
        out = verify_span(text, start=0, end=len(text))
        self.assertEqual(out["status"], "UNRESOLVED")

    def test_unrelated_participial_compound_is_unresolved(self):
        text = "attention-absorbing book"
        out = verify_span(text, start=0, end=len(text))
        self.assertEqual(out["status"], "UNRESOLVED")

    def test_wrong_span_does_not_smuggle_context(self):
        text = "The bank holds a loss-absorbing cushion."
        start = text.index("loss-absorbing")
        out = verify_span(text, start=start, end=len(text))
        self.assertEqual(out["status"], "UNRESOLVED")

    def test_exact_embedded_span_can_be_proved(self):
        text = "The bank holds a loss-absorbing cushion."
        start = text.index("loss-absorbing cushion")
        end = start + len("loss-absorbing cushion")
        out = verify_span(text, start=start, end=end)
        self.assertEqual(out["status"], "PROVED", out)

    def test_v10_recomputes_claim_from_source(self):
        out = verify_proof(
            RAW,
            source_id=SOURCE,
            claims=[{
                "claim_id": "disp",
                "kind": "CERTIFIED_PARTICIPIAL_DISPOSITION",
                "start": 0,
                "end": len(RAW),
            }],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED", out)
        self.assertEqual(
            out["proved_constraints"],
            [{"op": "ATOM", "id": SEMANTIC_ATOM}],
        )
        row = out["accepted_claims"][0]
        self.assertFalse(row["episodic_current_event_claimed"])
        self.assertFalse(row["concept_identity_claimed"])

    def test_v10_rejects_wrong_semantic_graph(self):
        out = verify_proof(
            RAW,
            source_id=SOURCE,
            claims=[{
                "claim_id": "disp",
                "kind": "CERTIFIED_PARTICIPIAL_DISPOSITION",
                "start": 0,
                "end": len(RAW),
                "semantic_graph": {
                    "head": "cushion",
                    "predicate": "recapitalise",
                    "object": "bank",
                    "reading": "DISPOSITIONAL",
                },
            }],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"], [])

    def test_phrase_can_prove_generic_loss_absorbing_concept(self):
        formula = atom(SEMANTIC_ATOM)
        out = prove(
            RAW,
            source_id=SOURCE,
            scope_id=SCOPE,
            target_concept_id="GENERIC_LOSS_ABSORBING_RESOURCE",
            direction="SOURCE_TO_TARGET",
            source_claims=[{
                "claim_id": "disp",
                "kind": "CERTIFIED_PARTICIPIAL_DISPOSITION",
                "start": 0,
                "end": len(RAW),
            }],
            target_formula=formula,
            concept_semantics_receipt={"candidate": True},
            concept_semantics_verifier=concept_verifier(
                formula,
                "GENERIC_LOSS_ABSORBING_RESOURCE",
            ),
            source_proof_verifier=verify_proof,
        )
        self.assertTrue(out["pass"], out)

    def test_phrase_does_not_prove_ccob_without_going_concern(self):
        formula = conj(
            atom(SEMANTIC_ATOM),
            atom("REGIME::GOING_CONCERN"),
        )
        out = prove(
            RAW,
            source_id=SOURCE,
            scope_id=SCOPE,
            target_concept_id="CCOB",
            direction="SOURCE_TO_TARGET",
            source_claims=[{
                "claim_id": "disp",
                "kind": "CERTIFIED_PARTICIPIAL_DISPOSITION",
                "start": 0,
                "end": len(RAW),
            }],
            target_formula=formula,
            concept_semantics_receipt={"candidate": True},
            concept_semantics_verifier=concept_verifier(formula, "CCOB"),
            source_proof_verifier=verify_proof,
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "UNKNOWN__ENTAILMENT_NOT_PROVED")
        self.assertFalse(out["nonentailment_authority"])

    def test_phrase_does_not_prove_tlac_without_resolution_semantics(self):
        formula = conj(
            atom(SEMANTIC_ATOM),
            atom("REGIME::RESOLUTION"),
            atom("FUNCTION::RECAPITALISATION"),
        )
        out = prove(
            RAW,
            source_id=SOURCE,
            scope_id=SCOPE,
            target_concept_id="TLAC",
            direction="SOURCE_TO_TARGET",
            source_claims=[{
                "claim_id": "disp",
                "kind": "CERTIFIED_PARTICIPIAL_DISPOSITION",
                "start": 0,
                "end": len(RAW),
            }],
            target_formula=formula,
            concept_semantics_receipt={"candidate": True},
            concept_semantics_verifier=concept_verifier(formula, "TLAC"),
            source_proof_verifier=verify_proof,
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "UNKNOWN__ENTAILMENT_NOT_PROVED")

    def test_no_terminal_authority(self):
        out = verify_span(RAW, start=0, end=len(RAW))
        self.assertFalse(out["terminal_authority"])
        proof = verify_proof(
            RAW,
            source_id=SOURCE,
            claims=[{
                "claim_id": "disp",
                "kind": "CERTIFIED_PARTICIPIAL_DISPOSITION",
                "start": 0,
                "end": len(RAW),
            }],
        )
        self.assertFalse(proof["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
