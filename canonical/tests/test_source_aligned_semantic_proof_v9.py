from __future__ import annotations
import json
import unittest

from canonical.runtime.certified_document_effect_field_v1 import parse_effect_fields
from canonical.runtime.certified_document_effect_relation_v1 import parse_effect_relations
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


class CertifiedDocumentEffectFieldV1Tests(unittest.TestCase):
    def test_exact_field_parses(self):
        out=parse_effect_fields(
            field_line("A.t","effect_class","DEFINE"),
            source="A",
        )
        self.assertEqual(out["status"],"PARSED",out)
        row=out["fields"][0]
        self.assertEqual(row["effect_id"],"A.t")
        self.assertEqual(row["field"],"effect_class")
        self.assertEqual(row["value"],"DEFINE")

    def test_null_time_is_exact_value(self):
        out=parse_effect_fields(
            field_line("A.t","valid_until",None),
            source="A",
        )
        self.assertEqual(out["status"],"PARSED",out)
        self.assertIsNone(out["fields"][0]["value"])

    def test_noncanonical_json_is_unresolved(self):
        payload=json.dumps(
            {"effect_id":"A.t","field":"value","value":"10"},
            indent=2,
        )
        out=parse_effect_fields("Effect field: "+payload,source="A")
        self.assertEqual(out["status"],"UNRESOLVED")

    def test_duplicate_semantic_slot_is_unresolved(self):
        line=field_line("A.t","value","10")
        out=parse_effect_fields(line+"\n"+line,source="A")
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertEqual(out["reason"],"DUPLICATE_EFFECT_FIELD_SLOT")

    def test_bad_effect_class_is_unresolved(self):
        out=parse_effect_fields(
            field_line("A.t","effect_class","RANDOM"),
            source="A",
        )
        self.assertEqual(out["status"],"UNRESOLVED")


class SourceAlignedSemanticProofV9Tests(unittest.TestCase):
    def test_exact_field_claim_is_proved(self):
        text=field_line("A.t","value",{"x":1})
        out=verify_proof(
            text,
            source_id="A",
            claims=[{
                "claim_id":"f",
                "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
                "effect_id":"A.t",
                "field":"value",
                "value":{"x":1},
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED",out)
        row=out["accepted_claims"][0]
        self.assertEqual(row["kind"],"CERTIFIED_DOCUMENT_EFFECT_FIELD")
        self.assertEqual(row["field"],"value")
        self.assertEqual(row["source_span_bytes"],[0,len(text.encode())])

    def test_changed_field_value_is_rejected(self):
        text=field_line("A.t","value","10")
        out=verify_proof(
            text,
            source_id="A",
            claims=[{
                "claim_id":"f",
                "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
                "effect_id":"A.t",
                "field":"value",
                "value":"99",
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED_WITH_REJECTIONS")
        self.assertFalse(any(
            x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_FIELD"
            for x in out["accepted_claims"]
        ))

    def test_v8_complete_relation_still_passes(self):
        text=relation_line()
        parsed=parse_effect_relations(text,source="A")["relations"][0]["effect"]
        semantic={k:v for k,v in parsed.items() if k!="source_locator"}
        out=verify_proof(
            text,
            source_id="A",
            claims=[{
                "claim_id":"r",
                "kind":"CERTIFIED_DOCUMENT_EFFECT_RELATION",
                "effect":semantic,
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED",out)
        self.assertEqual(
            out["accepted_claims"][0]["kind"],
            "CERTIFIED_DOCUMENT_EFFECT_RELATION",
        )


if __name__=="__main__":
    unittest.main()
