from __future__ import annotations
import json
import unittest

from canonical.runtime.source_explicit_semantic_claim_autofill_v2 import synthesize_missing_claims
from canonical.runtime.source_aligned_semantic_proof_v9 import verify_proof


def _dim_lines():
    return [
        "Effect IDs only for threshold: A.t.",
        "Effect A.t class: DEFINE.",
        'Effect A.t value JSON: "10".',
        "Effect A.t conditions JSON: {}.",
        "Effect A.t valid from: none.",
        "Effect A.t valid until: none.",
        "Effect A.t supersedes: none.",
    ]


def _relation():
    effect={
        "conditions":{},"effect_class":"DEFINE","effect_id":"A.t",
        "supersedes":[],"target_id":"threshold","valid_from":None,
        "valid_until":None,"value":"10",
    }
    return "Effect relation: "+json.dumps(
        effect,sort_keys=True,separators=(",",":"),ensure_ascii=False
    )


class SourceExplicitSemanticClaimAutofillV2Tests(unittest.TestCase):
    def test_empty_claims_compile_inventory_and_all_dimensions(self):
        source="\n".join(_dim_lines())
        out=synthesize_missing_claims(source,source_id="A",existing_claims=[])
        self.assertTrue(out["pass"],out)
        kinds=[x["kind"] for x in out["synthesized_claims"]]
        self.assertEqual(kinds.count("CERTIFIED_EFFECT_ID_INVENTORY"),1)
        self.assertEqual(kinds.count("CERTIFIED_DOCUMENT_EFFECT_DIMENSION"),6)
        checked=verify_proof(
            source,source_id="A",claims=out["synthesized_claims"]
        )
        self.assertEqual(checked["status"],"PROOF_CHECKED",checked)
        self.assertEqual(len(checked["accepted_claims"]),7)

    def test_wrong_existing_dimension_owns_slot_and_is_not_replaced(self):
        source="\n".join(_dim_lines())
        existing=[{
            "claim_id":"caller.bad.value",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_DIMENSION",
            "effect_id":"A.t",
            "dimension":"value",
            "value":"99",
        }]
        out=synthesize_missing_claims(
            source,source_id="A",existing_claims=existing
        )
        self.assertTrue(out["pass"],out)
        self.assertFalse(any(
            x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_DIMENSION"
            and x.get("effect_id")=="A.t"
            and x.get("dimension")=="value"
            for x in out["synthesized_claims"]
        ))
        checked=verify_proof(
            source,source_id="A",
            claims=existing+out["synthesized_claims"],
        )
        self.assertTrue(any(
            x.get("claim_id")=="caller.bad.value"
            for x in checked["rejected_claims"]
        ))

    def test_existing_full_relation_blocks_dimension_autofill_for_effect(self):
        source="\n".join(_dim_lines())
        wrong={
            "conditions":{},"effect_class":"DEFINE","effect_id":"A.t",
            "supersedes":[],"target_id":"threshold","valid_from":None,
            "valid_until":None,"value":"99",
        }
        existing=[{
            "claim_id":"caller.bad.relation",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_RELATION",
            "effect":wrong,
        }]
        out=synthesize_missing_claims(
            source,source_id="A",existing_claims=existing
        )
        self.assertTrue(out["pass"],out)
        self.assertFalse(any(
            x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_DIMENSION"
            and x.get("effect_id")=="A.t"
            for x in out["synthesized_claims"]
        ))

    def test_existing_dimension_blocks_full_relation_autofill_for_effect(self):
        source="\n".join([_relation(),'Effect A.t value JSON: "10".'])
        existing=[{
            "claim_id":"caller.value",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_DIMENSION",
            "effect_id":"A.t","dimension":"value","value":"10",
        }]
        out=synthesize_missing_claims(
            source,source_id="A",existing_claims=existing
        )
        self.assertTrue(out["pass"],out)
        self.assertFalse(any(
            x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_RELATION"
            and x.get("effect",{}).get("effect_id")=="A.t"
            for x in out["synthesized_claims"]
        ))

    def test_malformed_dimension_blocks_overlapping_autofill(self):
        source="\n".join([_relation(),*_dim_lines()])
        existing=[{
            "claim_id":"caller.malformed",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_DIMENSION",
            "effect_id":"A.t",
        }]
        out=synthesize_missing_claims(
            source,source_id="A",existing_claims=existing
        )
        self.assertTrue(out["pass"],out)
        self.assertFalse(any(
            x.get("kind") in {
                "CERTIFIED_DOCUMENT_EFFECT_RELATION",
                "CERTIFIED_DOCUMENT_EFFECT_DIMENSION",
            }
            for x in out["synthesized_claims"]
        ))

    def test_unstructured_prose_creates_no_dimension_claims(self):
        out=synthesize_missing_claims(
            "The threshold might change.",
            source_id="A",existing_claims=[],
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["synthesized_claims"],[])
        self.assertFalse(out["semantic_truth_authority"])


if __name__=="__main__":
    unittest.main()
