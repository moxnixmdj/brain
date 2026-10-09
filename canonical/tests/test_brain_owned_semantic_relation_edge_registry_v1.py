from __future__ import annotations
import unittest

from canonical.runtime.certified_bounded_semantic_extension_source_v1 import parse
from canonical.runtime import brain_owned_bounded_semantic_relation_edge_authority_v1 as bounded
from canonical.runtime import brain_owned_semantic_relation_edge_authority_v1 as identity
from canonical.runtime import brain_owned_semantic_relation_edge_registry_v1 as registry
from canonical.runtime.semantic_relation_entailment_dag_v1 import RECEIPT_SCHEMA


def source_text():
    return "\n".join([
        'Semantic universe: {"members":["a","b","c"],"scope_id":"s"}',
        'Semantic extension: {"concept_id":"L","members":["a"],"scope_id":"s"}',
        'Semantic extension: {"concept_id":"R","members":["a","b"],"scope_id":"s"}',
    ])


def bounded_evidence(*,relation="ENTAILS",scope="s",text=None):
    return {
        "schema":bounded.SCHEMA,
        "proof_class":bounded.PROOF_CLASS,
        "scope_id":scope,
        "source_id":"L",
        "target_id":"R",
        "relation":relation,
        "bounded_extension_source":{
            "source_id":"decl",
            "scope_id":scope,
            "source_text":text if text is not None else source_text(),
        },
    }


def identity_evidence():
    return {
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


class CertifiedBoundedSourceTests(unittest.TestCase):
    def test_exact_source_parses(self):
        out=parse(source_text(),source_id="decl")
        self.assertEqual(out["status"],"PARSED",out)
        self.assertEqual(len(out["universes"]),1)
        self.assertEqual(len(out["extensions"]),2)

    def test_unsorted_members_are_unresolved(self):
        text=source_text().replace('["a","b"]','["b","a"]')
        out=parse(text,source_id="decl")
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertIn("NOT_SORTED",out["reason"])

    def test_duplicate_extension_is_unresolved(self):
        text=source_text()+"\n"+'Semantic extension: {"concept_id":"L","members":["a"],"scope_id":"s"}'
        out=parse(text,source_id="decl")
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertIn("DUPLICATE_EXTENSION_SLOT",out["reason"])


class BoundedAuthorityTests(unittest.TestCase):
    def test_subset_emits_entails_receipt(self):
        raw=bounded_evidence()
        self.assertTrue(bounded.supports(raw))
        out=bounded.verify(raw)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["schema"],RECEIPT_SCHEMA)
        self.assertEqual(out["relation"],"ENTAILS")
        self.assertTrue(out["bounded_relation_proof"]["left_entails_right"])

    def test_witness_emits_not_entails_receipt(self):
        raw=bounded_evidence(relation="NOT_ENTAILS")
        raw["source_id"]="R"
        raw["target_id"]="L"
        out=bounded.verify(raw)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["relation"],"NOT_ENTAILS")
        self.assertEqual(
            out["bounded_relation_proof"]["left_not_right_witnesses"],
            ["b"],
        )

    def test_false_entailment_is_rejected_with_witness(self):
        raw=bounded_evidence()
        raw["source_id"]="R"
        raw["target_id"]="L"
        out=bounded.verify(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"ENTAILMENT_DISPROVED_OR_UNPROVED")
        self.assertEqual(out["left_not_right_witnesses"],["b"])

    def test_wrong_source_scope_fails_closed(self):
        raw=bounded_evidence()
        raw["bounded_extension_source"]["scope_id"]="other"
        out=bounded.verify(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"BOUNDED_EXTENSION_SOURCE_BINDING_INVALID")


class RegistryTests(unittest.TestCase):
    def test_registry_supports_both_internal_classes(self):
        self.assertTrue(registry.supports(bounded_evidence()))
        self.assertTrue(registry.supports(identity_evidence()))
        self.assertEqual(
            registry.supported_proof_classes(),
            ["EXPLICIT_BOUNDED_EXTENSION","EXPLICIT_SOURCE_IDENTITY"],
        )

    def test_registry_verifies_bounded(self):
        out=registry.verify(bounded_evidence())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proof_class"],"EXPLICIT_BOUNDED_EXTENSION")

    def test_registry_verifies_identity(self):
        out=registry.verify(identity_evidence())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proof_class"],"EXPLICIT_SOURCE_IDENTITY")

    def test_registry_rejects_unsupported(self):
        raw=bounded_evidence()
        raw["proof_class"]="MODEL_GUESS"
        self.assertFalse(registry.supports(raw))
        out=registry.verify(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"PROOF_CLASS_UNSUPPORTED")


if __name__=="__main__":
    unittest.main()
