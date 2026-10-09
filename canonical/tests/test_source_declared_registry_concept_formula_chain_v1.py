from __future__ import annotations

import json
import unittest

from canonical.runtime import bounded_authenticated_concept_universe_v1 as universe
from canonical.runtime.bounded_concept_formula_authority_v1 import (
    make_claim,
    verify_claim,
)
from canonical.runtime.source_declared_bounded_concept_registry_authority_v1 import (
    make_evidence,
    verify as verify_registry_authority,
)
from canonical.runtime.source_aligned_semantic_edge_authority_v1 import prove
from canonical.runtime.source_aligned_participial_disposition_proof_v1 import (
    verify_proof as verify_participial,
)
from canonical.runtime.bounded_participial_disposition_v1 import SEMANTIC_ATOM


SCOPE="finance:regcap:bounded:v1"
CONCEPT="GENERIC_LOSS_ABSORBING_RESOURCE"


def atom(name):
    return {"op":"ATOM","id":name}


def registry():
    return {
        "schema":universe.REGISTRY_SCHEMA,
        "registry_id":"loss-absorption-formulas-v1",
        "scope_id":SCOPE,
        "bounded_finite_registry":True,
        "concepts":[{
            "concept_id":CONCEPT,
            "surfaces":["generic loss absorbing resource"],
            "attributes":{
                "semantic_formula":atom(SEMANTIC_ATOM),
                "semantic_formula_relation":"LOGICAL_EQUIVALENCE_IN_SCOPE",
            },
            "terminal_signature_complete":True,
            "terminal_signature":{"family":"GENERIC_LOSS_ABSORPTION"},
        }],
        "observations":[],
    }


def authority_evidence(reg):
    checked=universe.validate_registry(reg)
    payload={
        "concept_semantics_authenticated":True,
        "registry_id":checked["registry"]["registry_id"],
        "registry_sha256":checked["registry_sha256"],
        "scope_completeness_authenticated":True,
        "scope_id":checked["registry"]["scope_id"],
    }
    line="Bounded concept registry authority: "+json.dumps(
        payload,sort_keys=True,separators=(",",":")
    )
    return make_evidence(line,source_id="authority:registry")


class Tests(unittest.TestCase):
    def test_source_declaration_mints_registry_authority_receipt(self):
        reg=registry()
        evidence=authority_evidence(reg)
        out=verify_registry_authority(evidence)
        self.assertTrue(out["pass"],out)
        checked=universe.validate_registry(reg)
        self.assertEqual(out["registry_sha256"],checked["registry_sha256"])
        self.assertEqual(out["registry_id"],reg["registry_id"])
        self.assertEqual(out["scope_id"],SCOPE)
        self.assertTrue(out["scope_completeness_authenticated"])
        self.assertTrue(out["concept_semantics_authenticated"])
        self.assertFalse(out["open_world_ontology_complete"])

    def test_bounded_concept_formula_verifies_without_external_callback(self):
        reg=registry()
        claim=make_claim(
            reg,
            concept_id=CONCEPT,
            authority_receipt=authority_evidence(reg),
        )
        out=verify_claim(claim,authority_verifier=None)
        self.assertTrue(out["pass"],out)
        self.assertEqual(
            out["schema"],
            "PROJECT_BRAIN_CONCEPT_SEMANTICS_AUTHORITY_RECEIPT_V1",
        )
        self.assertEqual(out["concept_id"],CONCEPT)

    def test_participial_source_to_concept_edge_needs_no_concept_callback(self):
        reg=registry()
        concept_claim=make_claim(
            reg,
            concept_id=CONCEPT,
            authority_receipt=authority_evidence(reg),
        )
        raw="loss-absorbing cushion"
        out=prove(
            raw,
            source_id="doc:A",
            scope_id=SCOPE,
            target_concept_id=CONCEPT,
            direction="SOURCE_TO_TARGET",
            source_claims=[{
                "claim_id":"disp",
                "kind":"CERTIFIED_PARTICIPIAL_DISPOSITION",
                "start":0,
                "end":len(raw),
            }],
            target_formula=atom(SEMANTIC_ATOM),
            concept_semantics_receipt=concept_claim,
            concept_semantics_verifier=None,
            source_proof_verifier=verify_participial,
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["edge_receipt"]["target_id"],CONCEPT)

    def test_tampered_registry_hash_in_declaration_fails(self):
        reg=registry()
        evidence=authority_evidence(reg)
        source=evidence["source_text"]
        checked=universe.validate_registry(reg)
        source=source.replace(checked["registry_sha256"],"0"*64)
        bad=make_evidence(source,source_id="authority:registry")
        claim=make_claim(reg,concept_id=CONCEPT,authority_receipt=bad)
        out=verify_claim(claim,authority_verifier=None)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "REGISTRY_CONCEPT_SEMANTICS_NOT_AUTHENTICATED",
        )

    def test_wrong_scope_declaration_cannot_authenticate_registry(self):
        reg=registry()
        checked=universe.validate_registry(reg)
        payload={
            "concept_semantics_authenticated":True,
            "registry_id":reg["registry_id"],
            "registry_sha256":checked["registry_sha256"],
            "scope_completeness_authenticated":True,
            "scope_id":"wrong",
        }
        line="Bounded concept registry authority: "+json.dumps(
            payload,sort_keys=True,separators=(",",":")
        )
        evidence=make_evidence(line,source_id="authority:registry")
        claim=make_claim(reg,concept_id=CONCEPT,authority_receipt=evidence)
        out=verify_claim(claim,authority_verifier=None)
        self.assertFalse(out["pass"])

    def test_tampered_concept_formula_still_fails(self):
        reg=registry()
        claim=make_claim(
            reg,
            concept_id=CONCEPT,
            authority_receipt=authority_evidence(reg),
        )
        claim["formula"]=atom("OTHER")
        out=verify_claim(claim,authority_verifier=None)
        self.assertFalse(out["pass"])


if __name__=="__main__":
    unittest.main()
