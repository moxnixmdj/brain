from __future__ import annotations

from hashlib import sha256
import unittest

from canonical.runtime.unified_cognitive_fabric_v1 import run
from canonical.runtime import brain_owned_scoped_domain_mapping_relation_edge_authority_v1 as scoped
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA,
    evidence_sha256,
)

RAW="loss-absorbing cushion"
RAW_SOURCE="doc:A"
SCOPE="finance:regulatory-capital:2026"
CONCEPT="CCOB"


def mention():
    return "MENTION:"+sha256(
        (RAW_SOURCE+"\n"+SCOPE+"\n"+RAW).encode("utf-8")
    ).hexdigest()


def edge(direction, *, model_only=False):
    left=mention()
    source_id,target_id=(
        (left,CONCEPT)
        if direction==scoped.MENTION_TO_CONCEPT
        else (CONCEPT,left)
    )
    relation_problem={"required_relation":"SEMANTIC_IDENTITY"}
    if model_only:
        relation_problem["candidate_relations"]=[
            {"relation":"SIMILAR","score":0.999,"source":"embedding"}
        ]
    else:
        relation_problem["explicit_definition_sources"]=[{
            "source_id":RAW_SOURCE,
            "scope_id":SCOPE,
            "source_text":"Loss-absorbing cushion means capital conservation buffer.",
        }]
    return {
        "schema":scoped.SCHEMA,
        "proof_class":scoped.PROOF_CLASS,
        "scope_id":SCOPE,
        "source_id":source_id,
        "target_id":target_id,
        "relation":"ENTAILS",
        "domain_mapping_source":{
            "source_id":RAW_SOURCE,
            "raw_span":RAW,
            "target_concept_id":CONCEPT,
            "required_relation":"SEMANTIC_IDENTITY",
            "edge_direction":direction,
            "candidate_concepts":[{
                "concept_id":CONCEPT,
                "surface":"capital conservation buffer",
                "required_atoms":[],
                "forbidden_atoms":[],
            }],
            "evidence":[],
            "candidate_semantic_atoms":[],
            "relation_problems":{CONCEPT:relation_problem},
        },
    }


def request(*, model_only=False):
    dag={
        "schema":EVIDENCE_SCHEMA,
        "scope_id":SCOPE,
        "left_id":mention(),
        "right_id":CONCEPT,
        "entailment_receipts":[
            edge(scoped.MENTION_TO_CONCEPT,model_only=model_only),
            edge(scoped.CONCEPT_TO_MENTION,model_only=model_only),
        ],
        "counterexample_receipts":[],
    }
    return {
        "payload":{
            "left_id":mention(),
            "right_id":CONCEPT,
            "left_surface":RAW,
            "right_surface":"capital conservation buffer",
            "scope_id":SCOPE,
            "required_relation":"LOGICAL_EQUIVALENCE_IN_SCOPE",
            "entailment_dag_evidence":dag,
            "expected_entailment_dag_sha256":evidence_sha256(dag),
        }
    }


class Tests(unittest.TestCase):
    def test_auto_route_uses_owned_registry_without_host_verifier(self):
        out=run(request())
        self.assertTrue(out["auto_routed"],out)
        self.assertEqual(out["mode"],"SEMANTIC_RELATION")
        self.assertTrue(out["inner_pass"],out)
        self.assertEqual(
            out["result"]["strongest_proved_relation"],
            "LOGICAL_EQUIVALENCE_IN_SCOPE",
        )
        self.assertTrue(
            out["result"]["brain_owned_relation_registry_v4_used"]
        )

    def test_similarity_only_still_fails_closed_without_host_verifier(self):
        out=run(request(model_only=True))
        self.assertTrue(out["auto_routed"],out)
        self.assertEqual(out["mode"],"SEMANTIC_RELATION")
        self.assertFalse(out["inner_pass"],out)
        self.assertFalse(
            out["result"]["brain_owned_relation_registry_v4_used"]
        )


if __name__=="__main__":
    unittest.main(verbosity=2)
