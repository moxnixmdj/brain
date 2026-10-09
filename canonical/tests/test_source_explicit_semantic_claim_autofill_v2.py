from __future__ import annotations
import json
import unittest

from canonical.runtime.source_explicit_semantic_claim_autofill_v2 import (
    synthesize_missing_claims,
)
from canonical.runtime.source_aligned_semantic_proof_v9 import verify_proof


def field_line(eid,field,value):
    return "Effect field: "+json.dumps(
        {"effect_id":eid,"field":field,"value":value},
        sort_keys=True,separators=(",",":"),ensure_ascii=False,
    )


def relation_line():
    effect={
        "conditions":{},"effect_class":"DEFINE","effect_id":"A.t",
        "supersedes":[],"target_id":"threshold","valid_from":None,
        "valid_until":None,"value":"10",
    }
    return "Effect relation: "+json.dumps(
        effect,sort_keys=True,separators=(",",":"),ensure_ascii=False
    )


class SourceExplicitSemanticClaimAutofillV2Tests(unittest.TestCase):
    def test_empty_claims_fill_explicit_fields(self):
        source="\n".join([
            field_line("A.t","effect_class","DEFINE"),
            field_line("A.t","value","10"),
        ])
        out=synthesize_missing_claims(
            source,source_id="A",existing_claims=[]
        )
        self.assertTrue(out["pass"],out)
        fields=[
            x for x in out["synthesized_claims"]
            if x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_FIELD"
        ]
        self.assertEqual(len(fields),2)
        checked=verify_proof(
            source,
            source_id="A",
            claims=out["synthesized_claims"],
        )
        self.assertEqual(checked["status"],"PROOF_CHECKED",checked)

    def test_existing_wrong_field_owns_slot_and_is_not_replaced(self):
        source=field_line("A.t","value","10")
        existing=[{
            "claim_id":"wrong",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            "effect_id":"A.t",
            "field":"value",
            "value":"99",
        }]
        out=synthesize_missing_claims(
            source,source_id="A",existing_claims=existing
        )
        self.assertTrue(out["pass"],out)
        self.assertFalse(any(
            x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_FIELD"
            for x in out["synthesized_claims"]
        ))
        checked=verify_proof(
            source,
            source_id="A",
            claims=existing+out["synthesized_claims"],
        )
        self.assertTrue(any(
            x.get("claim_id")=="wrong"
            for x in checked["rejected_claims"]
        ))

    def test_malformed_existing_field_blocks_all_field_autofill(self):
        source="\n".join([
            field_line("A.t","value","10"),
            field_line("A.t","conditions",{}),
        ])
        existing=[{
            "claim_id":"bad",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            "value":"10",
        }]
        out=synthesize_missing_claims(
            source,source_id="A",existing_claims=existing
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["field_synthesized_claim_count"],0)

    def test_v1_full_relation_autofill_is_preserved(self):
        source=relation_line()
        out=synthesize_missing_claims(
            source,source_id="A",existing_claims=[]
        )
        self.assertTrue(out["pass"],out)
        self.assertTrue(any(
            x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_RELATION"
            for x in out["synthesized_claims"]
        ))

    def test_unstructured_prose_creates_no_fields(self):
        out=synthesize_missing_claims(
            "The threshold may change.",
            source_id="A",
            existing_claims=[],
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["field_synthesized_claim_count"],0)


if __name__=="__main__":
    unittest.main()
