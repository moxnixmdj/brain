from __future__ import annotations
import json
import unittest

from canonical.runtime.certified_document_effect_relation_v1 import parse_effect_relations
from canonical.runtime.source_aligned_semantic_proof_v8 import verify_proof


def _payload(**overrides):
    row={
        "conditions":{},
        "effect_class":"REPLACE",
        "effect_id":"B.t",
        "supersedes":["A.t"],
        "target_id":"reporting.threshold",
        "valid_from":"2026-07-01",
        "valid_until":None,
        "value":"12",
    }
    row.update(overrides)
    return json.dumps(row,sort_keys=True,separators=(",",":"),ensure_ascii=False)


def _line(**overrides):
    return "Effect relation: "+_payload(**overrides)


class CertifiedDocumentEffectRelationV1Tests(unittest.TestCase):
    def test_exact_canonical_relation_parses(self):
        out=parse_effect_relations(_line(),source="doc")
        self.assertEqual(out["status"],"PARSED",out)
        self.assertEqual(len(out["relations"]),1)
        row=out["relations"][0]
        self.assertEqual(row["effect"]["effect_id"],"B.t")
        self.assertEqual(row["effect"]["effect_class"],"REPLACE")
        self.assertEqual(row["effect"]["source_locator"],"doc:0-"+str(len(_line().encode())))

    def test_noncanonical_json_is_unresolved(self):
        pretty=json.dumps(json.loads(_payload()),indent=2)
        out=parse_effect_relations("Effect relation: "+pretty,source="doc")
        self.assertEqual(out["status"],"UNRESOLVED")

    def test_invalid_cross_field_effect_fails_closed_to_unresolved(self):
        out=parse_effect_relations(
            _line(effect_class="REPLACE",supersedes=[]),
            source="doc",
        )
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertIn("EFFECT_RELATION_INVALID",out["reason"])

    def test_duplicate_effect_id_is_unresolved(self):
        text=_line()+"\n"+_line(value="13")
        out=parse_effect_relations(text,source="doc")
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertEqual(out["reason"],"DUPLICATE_EFFECT_RELATION_ID")


class SourceAlignedSemanticProofV8Tests(unittest.TestCase):
    def test_exact_relation_claim_is_proved(self):
        text=_line()
        parsed=parse_effect_relations(text,source="doc")["relations"][0]
        semantic={k:v for k,v in parsed["effect"].items() if k!="source_locator"}
        out=verify_proof(
            text,
            source_id="doc",
            claims=[{
                "claim_id":"rel",
                "kind":"CERTIFIED_DOCUMENT_EFFECT_RELATION",
                "effect":semantic,
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED",out)
        row=out["accepted_claims"][0]
        self.assertEqual(row["kind"],"CERTIFIED_DOCUMENT_EFFECT_RELATION")
        self.assertEqual(row["effect"]["value"],"12")
        self.assertTrue(
            row["constraint"]["id"].startswith("DOCUMENT_EFFECT_RELATION::doc::")
        )

    def test_changed_value_is_rejected(self):
        text=_line()
        effect=parse_effect_relations(text,source="doc")["relations"][0]["effect"]
        claimed={k:v for k,v in effect.items() if k!="source_locator"}; claimed["value"]="99"
        out=verify_proof(
            text,source_id="doc",
            claims=[{
                "claim_id":"rel",
                "kind":"CERTIFIED_DOCUMENT_EFFECT_RELATION",
                "effect":claimed,
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"],[])

    def test_changed_supersession_is_rejected(self):
        text=_line()
        effect=parse_effect_relations(text,source="doc")["relations"][0]["effect"]
        claimed={k:v for k,v in effect.items() if k!="source_locator"}; claimed["supersedes"]=[]
        out=verify_proof(
            text,source_id="doc",
            claims=[{
                "claim_id":"rel",
                "kind":"CERTIFIED_DOCUMENT_EFFECT_RELATION",
                "effect":claimed,
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"],[])

    def test_v7_scope_primitive_still_passes_through(self):
        text="Effect targets only: reporting.threshold."
        out=verify_proof(
            text,
            source_id="doc",
            claims=[{
                "claim_id":"scope",
                "kind":"CERTIFIED_EFFECT_TARGET_SCOPE",
                "target_ids":["reporting.threshold"],
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED",out)
        self.assertEqual(out["accepted_claims"][0]["kind"],"CERTIFIED_EFFECT_TARGET_SCOPE")


if __name__=="__main__":
    unittest.main()
