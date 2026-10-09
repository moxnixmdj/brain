from __future__ import annotations
from hashlib import sha256
import json
import unittest

from canonical.runtime.brain_owned_semantic_relation_edge_authority_v1 import (
    SCHEMA, PROOF_CLASS, supports, verify,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import RECEIPT_SCHEMA


def evidence(*,relation="ENTAILS",scope="s",text=None):
    source_text=text or "Reserve buffer means liquidity cushion."
    return {
        "schema":SCHEMA,
        "proof_class":PROOF_CLASS,
        "scope_id":scope,
        "source_id":"left",
        "target_id":"right",
        "source_surface":"reserve buffer",
        "target_surface":"liquidity cushion",
        "relation":relation,
        "explicit_definition_sources":[{
            "source_id":"doc",
            "scope_id":scope,
            "source_text":source_text,
        }],
    }


class Tests(unittest.TestCase):
    def test_supported_exact_definition_emits_standard_receipt(self):
        raw=evidence()
        self.assertTrue(supports(raw))
        out=verify(raw)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["schema"],RECEIPT_SCHEMA)
        self.assertEqual(out["relation"],"ENTAILS")
        self.assertEqual(out["source_id"],"left")
        self.assertEqual(out["target_id"],"right")
        self.assertEqual(
            out["evidence_sha256"],
            sha256(json.dumps(raw,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest(),
        )

    def test_nondefinition_does_not_prove_relation(self):
        out=verify(evidence(text="Reserve buffer and liquidity cushion are reviewed."))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"SEMANTIC_IDENTITY_NOT_PROVED")

    def test_wrong_scope_definition_fails_closed(self):
        raw=evidence()
        raw["explicit_definition_sources"][0]["scope_id"]="other"
        out=verify(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"DEFINITION_SOURCE_BINDING_INVALID")

    def test_not_entails_is_never_inferred_from_identity(self):
        out=verify(evidence(relation="NOT_ENTAILS"))
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "NOT_ENTAILS_NOT_DERIVABLE_FROM_SEMANTIC_IDENTITY_PROOF",
        )

    def test_unsupported_proof_class_is_not_supported(self):
        raw=evidence()
        raw["proof_class"]="MODEL_JUDGMENT"
        self.assertFalse(supports(raw))
        out=verify(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"PROOF_CLASS_UNSUPPORTED")


if __name__=="__main__":
    unittest.main()
