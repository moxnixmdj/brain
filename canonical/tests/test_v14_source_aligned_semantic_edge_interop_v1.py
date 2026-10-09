from __future__ import annotations

from hashlib import sha256
import json
import unittest

from canonical.runtime.source_aligned_semantic_proof_v9 import verify_proof as verify_v9
from canonical.runtime.source_aligned_semantic_edge_authority_v1 import (
    CONCEPT_SEMANTICS_RECEIPT_SCHEMA,
    prove,
)


def canon_sha(value):
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",",":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def field_line():
    payload={
        "effect_id":"A.t",
        "field":"value",
        "value":"10",
    }
    return "Effect field: "+json.dumps(
        payload,
        sort_keys=True,
        separators=(",",":"),
        ensure_ascii=False,
    )


def claim():
    return {
        "claim_id":"field.value",
        "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
        "effect_id":"A.t",
        "field":"value",
        "value":"10",
    }


def concept_verifier(formula,concept_id):
    def verify(_receipt):
        return {
            "pass":True,
            "schema":CONCEPT_SEMANTICS_RECEIPT_SCHEMA,
            "scope_id":"crossdoc:v14",
            "concept_id":concept_id,
            "formula_sha256":canon_sha(formula),
            "definition_relation":"LOGICAL_EQUIVALENCE_IN_SCOPE",
            "concept_semantics_authenticated":True,
            "formula_semantics_authenticated":True,
            "verification_authority_mutated":False,
            "receipt_sha256":"c"*64,
        }
    return verify


class V14SourceAlignedSemanticEdgeInteropTests(unittest.TestCase):
    def test_v9_field_atom_can_supply_authenticated_source_to_target_edge(self):
        raw=field_line()
        checked=verify_v9(
            raw,
            source_id="A",
            claims=[claim()],
        )
        self.assertEqual(checked["status"],"PROOF_CHECKED",checked)
        self.assertEqual(len(checked["proved_constraints"]),1)
        formula=checked["proved_constraints"][0]
        concept_id="EFFECT_FIELD_VALUE_A_T"

        out=prove(
            raw,
            source_id="A",
            scope_id="crossdoc:v14",
            target_concept_id=concept_id,
            direction="SOURCE_TO_TARGET",
            source_claims=[claim()],
            target_formula=formula,
            concept_semantics_receipt={"candidate":True},
            concept_semantics_verifier=concept_verifier(
                formula,concept_id
            ),
            source_proof_verifier=verify_v9,
        )

        self.assertTrue(out["pass"],out)
        self.assertTrue(out["semantic_edge_authority"])
        self.assertEqual(out["edge_receipt"]["relation"],"ENTAILS")
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_v9_field_proof_cannot_entail_unrelated_concept_atom(self):
        raw=field_line()
        formula={"op":"ATOM","id":"UNRELATED_SEMANTIC_ATOM"}
        concept_id="UNRELATED_CONCEPT"

        out=prove(
            raw,
            source_id="A",
            scope_id="crossdoc:v14",
            target_concept_id=concept_id,
            direction="SOURCE_TO_TARGET",
            source_claims=[claim()],
            target_formula=formula,
            concept_semantics_receipt={"candidate":True},
            concept_semantics_verifier=concept_verifier(
                formula,concept_id
            ),
            source_proof_verifier=verify_v9,
        )

        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"UNKNOWN__ENTAILMENT_NOT_PROVED")
        self.assertFalse(out["nonentailment_authority"])
        self.assertIsNone(out["edge_receipt"])


if __name__=="__main__":
    unittest.main()
