from __future__ import annotations
import unittest

from canonical.runtime.certified_semantic_implication_source_v1 import parse
from canonical.runtime import brain_owned_source_implication_closure_edge_authority_v1 as auth
from canonical.runtime import brain_owned_semantic_relation_edge_registry_v2 as registry
from canonical.runtime.semantic_relation_entailment_dag_v1 import RECEIPT_SCHEMA


def source():
    return "\n".join([
        "In scope finance, reserve_buffer entails loss_absorbing_resource.",
        "In scope finance, loss_absorbing_resource entails capital_cushion.",
    ])


def evidence(*,src="reserve_buffer",dst="capital_cushion",relation="ENTAILS",text=None):
    return {
        "schema":auth.SCHEMA,
        "proof_class":auth.PROOF_CLASS,
        "scope_id":"finance",
        "source_id":src,
        "target_id":dst,
        "relation":relation,
        "implication_source":{
            "source_id":"doc",
            "source_text":source() if text is None else text,
        },
    }


class ParserTests(unittest.TestCase):
    def test_exact_implications_parse(self):
        out=parse(source(),source_id="doc")
        self.assertEqual(out["status"],"PARSED",out)
        self.assertEqual(len(out["edges"]),2)
        self.assertEqual(out["edges"][0]["source_id"],"reserve_buffer")

    def test_duplicate_edge_fails_closed(self):
        text=source()+"\n"+"In scope finance, reserve_buffer entails loss_absorbing_resource."
        out=parse(text,source_id="doc")
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"DUPLICATE_ENTAILMENT_DECLARATION")

    def test_self_entailment_fails_closed(self):
        out=parse("In scope finance, x entails x.",source_id="doc")
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"SELF_ENTAILMENT_DECLARATION_FORBIDDEN")


class AuthorityTests(unittest.TestCase):
    def test_nonexplicit_two_edge_path_emits_entails(self):
        out=auth.verify(evidence())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["schema"],RECEIPT_SCHEMA)
        self.assertEqual(
            out["nonexplicit_entailment_path"],
            ["reserve_buffer","loss_absorbing_resource","capital_cushion"],
        )
        self.assertEqual(len(out["path_edge_receipts"]),2)

    def test_direct_relation_is_rejected_as_wrong_proof_class(self):
        text=source()+"\n"+"In scope finance, reserve_buffer entails capital_cushion."
        out=auth.verify(evidence(text=text))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"REQUESTED_RELATION_IS_EXPLICIT_NOT_NONEXPLICIT")

    def test_missing_path_is_unproved(self):
        out=auth.verify(evidence(dst="unrelated"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"NONEXPLICIT_ENTAILMENT_PATH_NOT_PROVED")

    def test_not_entails_is_never_inferred(self):
        out=auth.verify(evidence(relation="NOT_ENTAILS"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"ONLY_POSITIVE_ENTAILS_SUPPORTED")


class RegistryTests(unittest.TestCase):
    def test_registry_lists_new_class(self):
        self.assertIn("SOURCE_IMPLICATION_CLOSURE",registry.supported_proof_classes())
        self.assertTrue(registry.supports(evidence()))

    def test_registry_dispatches_new_class(self):
        out=registry.verify(evidence())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proof_class"],"SOURCE_IMPLICATION_CLOSURE")

    def test_registry_rejects_unknown_class(self):
        raw=evidence(); raw["proof_class"]="MODEL_SIMILARITY"
        out=registry.verify(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"PROOF_CLASS_UNSUPPORTED")


if __name__=="__main__":
    unittest.main()
