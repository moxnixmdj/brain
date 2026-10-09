from __future__ import annotations

import unittest

from canonical.runtime import bounded_authenticated_concept_universe_v1 as universe
from canonical.runtime.bounded_concept_formula_authority_v1 import (
    CLAIM_SCHEMA,
    make_claim,
    verify_claim,
)
from canonical.runtime.source_aligned_semantic_edge_authority_v1 import prove as prove_edge


SCOPE = "finance:regcap:bounded:v1"
TARGET = "CCOB"
RAW = "CET1 buffer above the regulatory minimum"
SOURCE = "doc:A"


def atom(name):
    return {"op": "ATOM", "id": name}


def conj(*rows):
    return {"op": "AND", "args": list(rows)}


def formula():
    return conj(
        atom("RESOURCE_CET1"),
        atom("ABOVE_REGULATORY_MINIMUM"),
        atom("FUNCTION_LOSS_ABSORPTION"),
    )


def registry(*, relation="LOGICAL_EQUIVALENCE_IN_SCOPE"):
    return {
        "schema": universe.REGISTRY_SCHEMA,
        "registry_id": "regcap-formulas-v1",
        "scope_id": SCOPE,
        "bounded_finite_registry": True,
        "concepts": [
            {
                "concept_id": TARGET,
                "surfaces": ["capital conservation buffer"],
                "attributes": {
                    "semantic_formula": formula(),
                    "semantic_formula_relation": relation,
                    "domain": "regulatory-capital",
                },
                "terminal_signature_complete": True,
                "terminal_signature": {"family": "CCOB"},
            },
            {
                "concept_id": "TLAC",
                "surfaces": ["total loss-absorbing capacity"],
                "attributes": {
                    "semantic_formula": conj(
                        atom("REGIME_RESOLUTION"),
                        atom("FUNCTION_LOSS_ABSORPTION"),
                        atom("FUNCTION_RECAPITALISATION"),
                    ),
                    "semantic_formula_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
                    "domain": "resolution",
                },
                "terminal_signature_complete": True,
                "terminal_signature": {"family": "TLAC"},
            },
        ],
        "observations": [],
    }


def authority_verifier(reg):
    checked = universe.validate_registry(reg)

    def verify(_receipt):
        return {
            "pass": True,
            "schema": universe.AUTHORITY_SCHEMA,
            "registry_sha256": checked["registry_sha256"],
            "registry_id": checked["registry"]["registry_id"],
            "scope_id": checked["registry"]["scope_id"],
            "scope_completeness_authenticated": True,
            "concept_semantics_authenticated": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "a" * 64,
        }

    return verify


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


class Tests(unittest.TestCase):
    def test_authenticated_registry_formula_mints_edge_compatible_receipt(self):
        reg = registry()
        claim = make_claim(
            reg,
            concept_id=TARGET,
            authority_receipt={"candidate": True},
        )
        out = verify_claim(
            claim,
            authority_verifier=authority_verifier(reg),
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["schema"],
            "PROJECT_BRAIN_CONCEPT_SEMANTICS_AUTHORITY_RECEIPT_V1",
        )
        self.assertEqual(out["concept_id"], TARGET)
        self.assertTrue(out["formula_semantics_authenticated"])
        self.assertFalse(out["open_world_ontology_complete"])

    def test_tampered_formula_fails_even_with_rehashed_claim(self):
        reg = registry()
        claim = make_claim(
            reg,
            concept_id=TARGET,
            authority_receipt={"candidate": True},
        )
        claim["formula"] = atom("WRONG")
        import hashlib, json

        core = {k: claim[k] for k in (
            "schema",
            "registry_sha256",
            "registry_id",
            "scope_id",
            "concept_id",
            "formula",
            "formula_sha256",
            "definition_relation",
            "authority_receipt",
            "registry",
        )}
        claim["claim_sha256"] = hashlib.sha256(
            json.dumps(
                core,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        out = verify_claim(
            claim,
            authority_verifier=authority_verifier(reg),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "CLAIM_FORMULA_MISMATCH")

    def test_missing_registry_authority_fails_closed(self):
        reg = registry()
        claim = make_claim(
            reg,
            concept_id=TARGET,
            authority_receipt={"candidate": True},
        )
        out = verify_claim(claim, authority_verifier=None)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "REGISTRY_CONCEPT_SEMANTICS_NOT_AUTHENTICATED",
        )

    def test_non_exact_registry_formula_cannot_be_promoted(self):
        reg = registry(relation="LEFT_ENTAILS_RIGHT")
        with self.assertRaisesRegex(
            ValueError,
            "SEMANTIC_FORMULA_RELATION_NOT_EXACT",
        ):
            make_claim(
                reg,
                concept_id=TARGET,
                authority_receipt={"candidate": True},
            )

    def test_formula_authority_drives_source_to_concept_edge(self):
        reg = registry()
        claim = make_claim(
            reg,
            concept_id=TARGET,
            authority_receipt={"candidate": True},
        )
        constraints = [
            atom("RESOURCE_CET1"),
            atom("ABOVE_REGULATORY_MINIMUM"),
            atom("FUNCTION_LOSS_ABSORPTION"),
        ]
        out = prove_edge(
            RAW,
            source_id=SOURCE,
            scope_id=SCOPE,
            target_concept_id=TARGET,
            direction="SOURCE_TO_TARGET",
            source_claims=[],
            target_formula=formula(),
            concept_semantics_receipt=claim,
            concept_semantics_verifier=lambda value: verify_claim(
                value,
                authority_verifier=authority_verifier(reg),
            ),
            source_proof_verifier=source_verifier(constraints),
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_edge_authority"])
        self.assertEqual(out["edge_receipt"]["target_id"], TARGET)
        self.assertFalse(out["terminal_authority"])

    def test_registry_formula_authority_never_claims_global_completion(self):
        reg = registry()
        claim = make_claim(
            reg,
            concept_id=TARGET,
            authority_receipt={"candidate": True},
        )
        out = verify_claim(
            claim,
            authority_verifier=authority_verifier(reg),
        )
        self.assertTrue(out["pass"])
        self.assertFalse(out["open_world_ontology_complete"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
