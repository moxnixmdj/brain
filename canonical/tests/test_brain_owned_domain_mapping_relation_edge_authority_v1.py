from __future__ import annotations
from hashlib import sha256
import unittest

from canonical.runtime import brain_owned_domain_mapping_relation_edge_authority_v1 as domain
from canonical.runtime import brain_owned_semantic_relation_edge_registry_v3 as registry
from canonical.runtime.semantic_relation_entailment_dag_v1 import RECEIPT_SCHEMA
from canonical.runtime import brain_owned_semantic_relation_edge_authority_v1 as identity
from canonical.runtime import brain_owned_source_implication_closure_edge_authority_v1 as implication
from canonical.runtime import brain_owned_bounded_semantic_relation_edge_authority_v1 as bounded

RAW="loss-absorbing cushion"
SCOPE="finance:regulatory-capital:2026"
RAW_SOURCE="doc:A"
TARGET="CCOB"

def mention_id():
    return "MENTION:"+sha256(
        (RAW_SOURCE+"\n"+SCOPE+"\n"+RAW).encode("utf-8")
    ).hexdigest()

def candidate():
    return {
        "concept_id":TARGET,
        "surface":"capital conservation buffer",
        "required_atoms":[],
        "forbidden_atoms":[],
    }

def raw(*,model_only=False,source_id=None):
    relation_problem={
        "required_relation":"LEFT_ENTAILS_RIGHT",
    }
    if model_only:
        relation_problem["candidate_relations"]=[{
            "relation":"SIMILAR","score":0.999,"source":"embedding",
        }]
    else:
        relation_problem["explicit_definition_sources"]=[{
            "source_id":RAW_SOURCE,
            "scope_id":SCOPE,
            "source_text":"Loss-absorbing cushion means capital conservation buffer.",
        }]
    return {
        "schema":domain.SCHEMA,
        "proof_class":domain.PROOF_CLASS,
        "scope_id":SCOPE,
        "source_id":source_id or mention_id(),
        "target_id":TARGET,
        "relation":"ENTAILS",
        "domain_mapping_source":{
            "source_id":RAW_SOURCE,
            "raw_span":RAW,
            "candidate_concepts":[candidate()],
            "evidence":[],
            "candidate_semantic_atoms":[],
            "relation_problems":{TARGET:relation_problem},
        },
    }

class DomainMappingEdgeAuthorityTests(unittest.TestCase):
    def test_explicit_definition_emits_standard_entails_receipt(self):
        out=domain.verify(raw())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["schema"],RECEIPT_SCHEMA)
        self.assertEqual(out["relation"],"ENTAILS")
        self.assertEqual(out["source_id"],mention_id())
        self.assertEqual(out["target_id"],TARGET)
        self.assertEqual(out["proof_class"],domain.PROOF_CLASS)
        self.assertEqual(
            out["domain_mapping_certificate"]["predicate_truth"],"TRUE"
        )

    def test_similarity_only_never_mints_edge(self):
        out=domain.verify(raw(model_only=True))
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["reason"],"DOMAIN_MAPPING_RELATION_NOT_PROVED")
        self.assertEqual(out["predicate_truth"],"UNKNOWN")

    def test_raw_mention_endpoint_rebinding_fails_closed(self):
        out=domain.verify(raw(source_id="MENTION:wrong"))
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],"EDGE_SOURCE_ID_DOES_NOT_BIND_RAW_MENTION"
        )

    def test_target_must_be_declared_candidate(self):
        row=raw()
        row["target_id"]="TLAC"
        out=domain.verify(row)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"TARGET_CONCEPT_NOT_IN_CANDIDATE_SET")

class RegistryV3Tests(unittest.TestCase):
    def test_registry_supports_domain_mapping_class(self):
        self.assertTrue(registry.supports(raw()))
        self.assertIn(
            "DOMAIN_MAPPING_RELATION",
            registry.supported_proof_classes(),
        )

    def test_registry_lists_all_inherited_and_new_classes(self):
        self.assertEqual(
            registry.supported_proof_classes(),
            [
                "DOMAIN_MAPPING_RELATION",
                "EXPLICIT_BOUNDED_EXTENSION",
                "EXPLICIT_SOURCE_IDENTITY",
                "SOURCE_IMPLICATION_CLOSURE",
            ],
        )

    def test_can_prove_rejects_similarity_only_domain_candidate(self):
        self.assertTrue(registry.can_prove(raw()))
        self.assertFalse(registry.can_prove(raw(model_only=True)))

    def test_registry_preserves_explicit_identity(self):
        evidence={
            "schema":identity.SCHEMA,
            "proof_class":identity.PROOF_CLASS,
            "scope_id":"s",
            "source_id":"left",
            "target_id":"right",
            "source_surface":"reserve buffer",
            "target_surface":"liquidity cushion",
            "relation":"ENTAILS",
            "explicit_definition_sources":[{
                "source_id":"doc",
                "scope_id":"s",
                "source_text":"Reserve buffer means liquidity cushion.",
            }],
        }
        out=registry.verify(evidence)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proof_class"],"EXPLICIT_SOURCE_IDENTITY")

    def test_registry_recomputes_domain_mapping_edge(self):
        out=registry.verify(raw())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proof_class"],"DOMAIN_MAPPING_RELATION")

    def test_unsupported_class_stays_fail_closed(self):
        row=raw()
        row["proof_class"]="MODEL_GUESS"
        out=registry.verify(row)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"PROOF_CLASS_UNSUPPORTED")


    def test_not_entails_is_not_in_authority_surface(self):
        row=raw()
        row["relation"]="NOT_ENTAILS"
        out=domain.verify(row)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"ONLY_POSITIVE_ENTAILS_SUPPORTED")

    def test_registry_preserves_source_implication_closure(self):
        text="\n".join([
            "In scope s, a entails b.",
            "In scope s, b entails c.",
        ])
        evidence={
            "schema":implication.SCHEMA,
            "proof_class":implication.PROOF_CLASS,
            "scope_id":"s",
            "source_id":"a",
            "target_id":"c",
            "relation":"ENTAILS",
            "implication_source":{
                "source_id":"decl",
                "source_text":text,
            },
        }
        out=registry.verify(evidence)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proof_class"],implication.PROOF_CLASS)

    def test_registry_preserves_bounded_extension(self):
        text="\n".join([
            'Semantic universe: {"members":["a","b"],"scope_id":"s"}',
            'Semantic extension: {"concept_id":"L","members":["a"],"scope_id":"s"}',
            'Semantic extension: {"concept_id":"R","members":["a","b"],"scope_id":"s"}',
        ])
        evidence={
            "schema":bounded.SCHEMA,
            "proof_class":bounded.PROOF_CLASS,
            "scope_id":"s",
            "source_id":"L",
            "target_id":"R",
            "relation":"ENTAILS",
            "bounded_extension_source":{
                "source_id":"decl","scope_id":"s","source_text":text,
            },
        }
        out=registry.verify(evidence)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proof_class"],bounded.PROOF_CLASS)

if __name__=="__main__":
    unittest.main()
