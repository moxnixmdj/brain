from __future__ import annotations

from hashlib import sha256
import json
import unittest

from canonical.runtime.bounded_participial_disposition_v1 import SEMANTIC_ATOM
from canonical.runtime.certified_document_effect_field_edge_v1 import field_concept_id
from canonical.runtime.source_aligned_semantic_edge_authority_v1 import (
    EVIDENCE_SCHEMA as COMPOSITIONAL_SCHEMA,
)
from canonical.runtime.brain_owned_concept_semantics_authority_v1 import (
    EVIDENCE_SCHEMA as CONCEPT_EVIDENCE_SCHEMA,
)
from canonical.runtime.brain_owned_bounded_semantic_relation_edge_authority_v1 import (
    SCHEMA as BOUNDED_SCHEMA,
    PROOF_CLASS as BOUNDED_CLASS,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA as DAG_SCHEMA,
    evidence_sha256,
    prove as prove_dag,
)
from canonical.runtime import brain_owned_semantic_relation_edge_registry_v2 as registry


RAW="loss-absorbing cushion"
SOURCE="doc:A"
SCOPE="scope:v19"
MID="LOSS_ABSORPTION_DISPOSITION"


def canon(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def mention():
    return "MENTION:"+sha256((SOURCE+"\n"+SCOPE+"\n"+RAW).encode()).hexdigest()


def concept_formula():
    return {"op":"ATOM","id":SEMANTIC_ATOM}


def compositional_edge():
    formula=concept_formula()
    concept_source="Concept semantics: "+canon({
        "concept_id":MID,
        "formula":formula,
        "scope_id":SCOPE,
    })
    return {
        "schema":COMPOSITIONAL_SCHEMA,
        "raw_span":RAW,
        "source_id":SOURCE,
        "scope_id":SCOPE,
        "target_concept_id":MID,
        "direction":"SOURCE_TO_TARGET",
        "source_claims":[{
            "claim_id":"participial",
            "kind":"CERTIFIED_PARTICIPIAL_DISPOSITION",
            "start":0,
            "end":len(RAW),
        }],
        "target_formula":formula,
        "concept_semantics_receipt":{
            "schema":CONCEPT_EVIDENCE_SCHEMA,
            "scope_id":SCOPE,
            "concept_id":MID,
            "formula":formula,
            "source":{
                "source_id":"concept-doc",
                "scope_id":SCOPE,
                "source_text":concept_source,
            },
        },
    }


def bounded_edge(target):
    declaration="\n".join([
        "Semantic universe: "+canon({"members":["a","b"],"scope_id":SCOPE}),
        "Semantic extension: "+canon({
            "concept_id":MID,"members":["a"],"scope_id":SCOPE,
        }),
        "Semantic extension: "+canon({
            "concept_id":target,"members":["a","b"],"scope_id":SCOPE,
        }),
    ])
    return {
        "schema":BOUNDED_SCHEMA,
        "proof_class":BOUNDED_CLASS,
        "scope_id":SCOPE,
        "source_id":MID,
        "target_id":target,
        "relation":"ENTAILS",
        "bounded_extension_source":{
            "source_id":"bounded-doc",
            "scope_id":SCOPE,
            "source_text":declaration,
        },
    }


class Tests(unittest.TestCase):
    def test_registry_supports_compositional_edge(self):
        edge=compositional_edge()
        self.assertTrue(registry.supports(edge))
        out=registry.verify(edge)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["source_id"],mention())
        self.assertEqual(out["target_id"],MID)

    def test_mixed_registered_proof_classes_compose_transitively(self):
        target=field_concept_id(
            scope_id=SCOPE,
            effect_id="A.t",
            field="value",
            value="10",
        )
        dag={
            "schema":DAG_SCHEMA,
            "scope_id":SCOPE,
            "left_id":mention(),
            "right_id":target,
            "entailment_receipts":[
                compositional_edge(),
                bounded_edge(target),
            ],
            "counterexample_receipts":[],
        }
        out=prove_dag(
            dag,
            expected_evidence_sha256=evidence_sha256(dag),
            relation_verifier=registry.verify,
        )
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["left_entails_right"])
        self.assertEqual(
            out["left_to_right_path"],
            [mention(),MID,target],
        )

    def test_compositional_formula_tamper_breaks_chain(self):
        edge=compositional_edge()
        edge["target_formula"]={"op":"ATOM","id":"OTHER"}
        self.assertTrue(registry.supports(edge))
        out=registry.verify(edge)
        self.assertFalse(out["pass"])

    def test_registry_lists_three_proof_classes(self):
        self.assertEqual(
            registry.supported_proof_classes(),
            [
                "COMPOSITIONAL_SOURCE_TO_CONCEPT",
                "EXPLICIT_BOUNDED_EXTENSION",
                "EXPLICIT_SOURCE_IDENTITY",
            ],
        )


if __name__=="__main__":
    unittest.main()
