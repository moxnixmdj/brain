from __future__ import annotations

from hashlib import sha256
import unittest

from canonical.runtime import brain_owned_scoped_domain_mapping_relation_edge_authority_v1 as scoped
from canonical.runtime import brain_owned_semantic_relation_edge_registry_v4 as registry
from canonical.runtime import brain_owned_semantic_relation_edge_registry_v3 as registry_v3
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA,
    evidence_sha256,
    prove,
)

RAW="loss-absorbing cushion"
RAW_SOURCE="doc:A"
SCOPE="finance:regulatory-capital:2026"
CONCEPT="CCOB"


def mention_id():
    return "MENTION:"+sha256(
        (RAW_SOURCE+"\n"+SCOPE+"\n"+RAW).encode("utf-8")
    ).hexdigest()


def candidate():
    return {
        "concept_id":CONCEPT,
        "surface":"capital conservation buffer",
        "required_atoms":[],
        "forbidden_atoms":[],
    }


def edge(*,direction,required_relation="SEMANTIC_IDENTITY",model_only=False):
    mention=mention_id()
    if direction==scoped.MENTION_TO_CONCEPT:
        source_id,target_id=mention,CONCEPT
    else:
        source_id,target_id=CONCEPT,mention

    relation_problem={"required_relation":required_relation}
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
            "required_relation":required_relation,
            "edge_direction":direction,
            "candidate_concepts":[candidate()],
            "evidence":[],
            "candidate_semantic_atoms":[],
            "relation_problems":{CONCEPT:relation_problem},
        },
    }


class ScopedDomainMappingEdgeTests(unittest.TestCase):
    def test_identity_proves_forward_edge(self):
        out=scoped.verify(edge(direction=scoped.MENTION_TO_CONCEPT))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["source_id"],mention_id())
        self.assertEqual(out["target_id"],CONCEPT)
        self.assertEqual(out["relation"],"ENTAILS")
        self.assertEqual(out["proved_required_relation"],"SEMANTIC_IDENTITY")

    def test_identity_proves_reverse_edge(self):
        out=scoped.verify(edge(direction=scoped.CONCEPT_TO_MENTION))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["source_id"],CONCEPT)
        self.assertEqual(out["target_id"],mention_id())
        self.assertEqual(out["relation"],"ENTAILS")

    def test_two_identity_edges_prove_scoped_logical_equivalence(self):
        left=mention_id()
        dag={
            "schema":EVIDENCE_SCHEMA,
            "scope_id":SCOPE,
            "left_id":left,
            "right_id":CONCEPT,
            "entailment_receipts":[
                edge(direction=scoped.MENTION_TO_CONCEPT),
                edge(direction=scoped.CONCEPT_TO_MENTION),
            ],
            "counterexample_receipts":[],
        }
        out=prove(
            dag,
            expected_evidence_sha256=evidence_sha256(dag),
            relation_verifier=registry.verify,
        )
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["logical_equivalence_in_scope"],out)
        self.assertEqual(out["strongest_proved_relation"],"LOGICAL_EQUIVALENCE_IN_SCOPE")
        self.assertEqual(out["left_to_right_path"],[left,CONCEPT])
        self.assertEqual(out["right_to_left_path"],[CONCEPT,left])

    def test_one_way_relation_cannot_authorize_reverse_edge(self):
        out=scoped.verify(edge(
            direction=scoped.CONCEPT_TO_MENTION,
            required_relation="LEFT_ENTAILS_RIGHT",
        ))
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "REQUIRED_RELATION_DOES_NOT_AUTHORIZE_EDGE_DIRECTION",
        )

    def test_similarity_only_never_mints_either_direction(self):
        for direction in (
            scoped.MENTION_TO_CONCEPT,
            scoped.CONCEPT_TO_MENTION,
        ):
            with self.subTest(direction=direction):
                out=scoped.verify(edge(direction=direction,model_only=True))
                self.assertFalse(out["pass"],out)
                self.assertEqual(out["reason"],"SCOPED_DOMAIN_MAPPING_RELATION_NOT_PROVED")

    def test_endpoint_rebinding_fails_closed(self):
        row=edge(direction=scoped.CONCEPT_TO_MENTION)
        row["source_id"]="wrong"
        out=scoped.verify(row)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"EDGE_ENDPOINT_BINDING_INVALID")

    def test_registry_v4_preserves_v3_classes_and_adds_one(self):
        old=set(registry_v3.supported_proof_classes())
        new=set(registry.supported_proof_classes())
        self.assertEqual(new-old,{scoped.PROOF_CLASS})
        self.assertEqual(old-new,set())

    def test_registry_v4_recomputes_scoped_edge(self):
        row=edge(direction=scoped.CONCEPT_TO_MENTION)
        self.assertTrue(registry.can_prove(row))
        out=registry.verify(row)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proof_class"],scoped.PROOF_CLASS)


if __name__=="__main__":
    unittest.main(verbosity=2)
