from __future__ import annotations

from hashlib import sha256
import unittest
from unittest.mock import Mock

from canonical.runtime import semantic_relation_control_v2 as control
from canonical.runtime import brain_owned_scoped_domain_mapping_relation_edge_authority_v1 as scoped
from canonical.runtime import brain_owned_semantic_relation_edge_registry_v4 as registry
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


def dag(*, model_only=False):
    value={
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
    return value


def problem(*, model_only=False):
    evidence=dag(model_only=model_only)
    return {
        "left_id":mention(),
        "right_id":CONCEPT,
        "left_surface":RAW,
        "right_surface":"capital conservation buffer",
        "scope_id":SCOPE,
        "required_relation":"LOGICAL_EQUIVALENCE_IN_SCOPE",
        "entailment_dag_evidence":evidence,
        "expected_entailment_dag_sha256":evidence_sha256(evidence),
    }


class Tests(unittest.TestCase):
    def test_owned_registry_closes_scoped_equivalence_without_host_verifier(self):
        out=control.resolve(problem())
        self.assertTrue(out["pass"],out)
        self.assertEqual(
            out["strongest_proved_relation"],
            "LOGICAL_EQUIVALENCE_IN_SCOPE",
        )
        self.assertTrue(out["brain_owned_relation_registry_v4_used"])
        self.assertEqual(
            out["relation_edge_verifier_source"],
            "BRAIN_OWNED_REGISTRY_V4",
        )

    def test_similarity_only_dag_never_gets_internal_authority(self):
        out=control.resolve(problem(model_only=True))
        self.assertFalse(out["pass"],out)
        self.assertFalse(out["brain_owned_relation_registry_v4_used"])
        self.assertEqual(out["relation_edge_verifier_source"],"NONE")
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__ENTAILMENT_DAG_EVIDENCE_INVALID",
        )

    def test_explicit_verifier_keeps_precedence(self):
        verifier=Mock(side_effect=registry.verify)
        out=control.resolve(problem(),relation_edge_verifier=verifier)
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["brain_owned_relation_registry_v4_used"])
        self.assertEqual(out["relation_edge_verifier_source"],"CALLER_SUPPLIED")
        self.assertEqual(verifier.call_count,2)


if __name__=="__main__":
    unittest.main(verbosity=2)
