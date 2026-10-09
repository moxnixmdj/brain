from __future__ import annotations
import unittest

from canonical.runtime.certified_document_effect_dimension_v1 import parse_effect_dimensions
from canonical.runtime.source_aligned_semantic_proof_v9 import verify_proof


class CertifiedDocumentEffectDimensionV1Tests(unittest.TestCase):
    def test_independent_dimensions_parse(self):
        text="\n".join([
            "Effect B.t class: REPLACE.",
            'Effect B.t value JSON: "12".',
            'Effect B.t conditions JSON: {"small":true}.',
            "Effect B.t valid from: 2026-07-01.",
            "Effect B.t valid until: none.",
            "Effect B.t supersedes: A.t.",
            "Effect B.t target: threshold.",
        ])
        out=parse_effect_dimensions(text,source="B")
        self.assertEqual(out["status"],"PARSED",out)
        rows={(x["effect_id"],x["dimension"]):x["value"] for x in out["dimensions"]}
        self.assertEqual(rows[("B.t","effect_class")],"REPLACE")
        self.assertEqual(rows[("B.t","value")],"12")
        self.assertEqual(rows[("B.t","conditions")],{"small":True})
        self.assertEqual(rows[("B.t","valid_from")],"2026-07-01")
        self.assertIsNone(rows[("B.t","valid_until")])
        self.assertEqual(rows[("B.t","supersedes")],["A.t"])
        self.assertEqual(rows[("B.t","target")],"threshold")

    def test_duplicate_same_dimension_is_unresolved(self):
        text="Effect A.t class: DEFINE.\nEffect A.t class: REPLACE."
        out=parse_effect_dimensions(text,source="A")
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertEqual(out["reason"],"DUPLICATE_EFFECT_DIMENSION_DECLARATION")

    def test_noncanonical_json_value_is_unresolved(self):
        out=parse_effect_dimensions('Effect A.t value JSON: { "x": 1 }.',source="A")
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertIn("VALUE_JSON_NOT_CANONICAL",out["reason"])

    def test_invalid_date_is_unresolved(self):
        out=parse_effect_dimensions("Effect A.t valid from: 2026-99-01.",source="A")
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertIn("VALID_FROM_INVALID",out["reason"])


class SourceAlignedSemanticProofV9Tests(unittest.TestCase):
    def test_exact_dimension_is_accepted(self):
        text="Effect B.t class: REPLACE."
        out=verify_proof(
            text,source_id="B",
            claims=[{
                "claim_id":"c",
                "kind":"CERTIFIED_DOCUMENT_EFFECT_DIMENSION",
                "effect_id":"B.t",
                "dimension":"effect_class",
                "value":"REPLACE",
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED",out)
        row=out["accepted_claims"][0]
        self.assertEqual(row["dimension"],"effect_class")
        self.assertEqual(row["value"],"REPLACE")

    def test_wrong_dimension_value_is_rejected(self):
        text='Effect B.t value JSON: "12".'
        out=verify_proof(
            text,source_id="B",
            claims=[{
                "claim_id":"v",
                "kind":"CERTIFIED_DOCUMENT_EFFECT_DIMENSION",
                "effect_id":"B.t",
                "dimension":"value",
                "value":"13",
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"],[])

    def test_unstructured_prose_cannot_mint_dimension(self):
        out=verify_proof(
            "The amendment seems to replace the threshold.",
            source_id="B",
            claims=[{
                "claim_id":"c",
                "kind":"CERTIFIED_DOCUMENT_EFFECT_DIMENSION",
                "effect_id":"B.t",
                "dimension":"effect_class",
                "value":"REPLACE",
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"],[])

    def test_v8_full_relation_still_passes_through(self):
        text='Effect relation: {"conditions":{},"effect_class":"DEFINE","effect_id":"A.t","supersedes":[],"target_id":"threshold","valid_from":null,"valid_until":null,"value":"10"}'
        from canonical.runtime.certified_document_effect_relation_v1 import parse_effect_relations
        parsed=parse_effect_relations(text,source="A")["relations"][0]["effect"]
        semantic={k:v for k,v in parsed.items() if k!="source_locator"}
        out=verify_proof(
            text,source_id="A",
            claims=[{
                "claim_id":"r",
                "kind":"CERTIFIED_DOCUMENT_EFFECT_RELATION",
                "effect":semantic,
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED",out)
        self.assertEqual(out["accepted_claims"][0]["kind"],"CERTIFIED_DOCUMENT_EFFECT_RELATION")


if __name__=="__main__":
    unittest.main()
