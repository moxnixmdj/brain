from __future__ import annotations
import unittest

from canonical.runtime.certified_effect_target_scope_v1 import parse_effect_target_scope
from canonical.runtime.source_aligned_semantic_proof_v7 import verify_proof


class CertifiedEffectTargetScopeV1Tests(unittest.TestCase):
    def test_embedded_single_scope_line_parses(self):
        text=(
            "Policy title\n"
            "Effect targets only: reporting.threshold, liquidity.buffer.\n"
            "Other prose remains semantically unresolved.\n"
        )
        out=parse_effect_target_scope(text,source="doc")
        self.assertEqual(out["status"],"PARSED",out)
        self.assertEqual(
            out["parse"]["target_ids"],
            ["liquidity.buffer","reporting.threshold"],
        )
        self.assertGreater(out["parse"]["source_span"][0],0)

    def test_duplicate_scope_declarations_are_unresolved(self):
        text=(
            "Effect targets only: x.\n"
            "Effect targets only: y.\n"
        )
        out=parse_effect_target_scope(text,source="doc")
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertEqual(out["declaration_count"],2)

    def test_duplicate_target_is_unresolved(self):
        out=parse_effect_target_scope(
            "Effect targets only: x, x.",
            source="doc",
        )
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertEqual(out["reason"],"DUPLICATE_TARGET_IN_SCOPE_DECLARATION")


class SourceAlignedSemanticProofV7Tests(unittest.TestCase):
    def test_exact_claimed_scope_is_proved(self):
        text="Effect targets only: reporting.threshold, liquidity.buffer."
        out=verify_proof(
            text,
            source_id="doc",
            claims=[{
                "claim_id":"scope",
                "kind":"CERTIFIED_EFFECT_TARGET_SCOPE",
                "target_ids":["reporting.threshold","liquidity.buffer"],
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED",out)
        row=out["accepted_claims"][0]
        self.assertEqual(
            row["target_ids"],
            ["liquidity.buffer","reporting.threshold"],
        )
        self.assertTrue(
            row["constraint"]["id"].startswith("EFFECT_TARGET_SCOPE::doc::")
        )

    def test_wrong_target_set_is_rejected(self):
        text="Effect targets only: reporting.threshold."
        out=verify_proof(
            text,
            source_id="doc",
            claims=[{
                "claim_id":"scope",
                "kind":"CERTIFIED_EFFECT_TARGET_SCOPE",
                "target_ids":["other.target"],
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"],[])

    def test_unstructured_prose_cannot_mint_scope(self):
        text="This probably changes only the reporting threshold."
        out=verify_proof(
            text,
            source_id="doc",
            claims=[{
                "claim_id":"scope",
                "kind":"CERTIFIED_EFFECT_TARGET_SCOPE",
                "target_ids":["reporting.threshold"],
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"],[])


    def test_exact_effect_id_inventory_is_proved(self):
        text=(
            "Effect targets only: reporting.threshold.\n"
            "Effect IDs only for reporting.threshold: B.t, C.t.\n"
        )
        out=verify_proof(
            text,
            source_id="doc",
            claims=[{
                "claim_id":"inventory",
                "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
                "target_id":"reporting.threshold",
                "effect_ids":["C.t","B.t"],
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED",out)
        row=out["accepted_claims"][0]
        self.assertEqual(row["target_id"],"reporting.threshold")
        self.assertEqual(row["effect_ids"],["B.t","C.t"])
        self.assertTrue(
            row["constraint"]["id"].startswith("EFFECT_ID_INVENTORY::doc::")
        )

    def test_wrong_effect_id_inventory_is_rejected(self):
        text="Effect IDs only for reporting.threshold: B.t."
        out=verify_proof(
            text,
            source_id="doc",
            claims=[{
                "claim_id":"inventory",
                "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
                "target_id":"reporting.threshold",
                "effect_ids":["X.t"],
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"],[])

    def test_duplicate_target_inventory_declaration_is_not_certifiable(self):
        text=(
            "Effect IDs only for reporting.threshold: B.t.\n"
            "Effect IDs only for reporting.threshold: C.t.\n"
        )
        out=verify_proof(
            text,
            source_id="doc",
            claims=[{
                "claim_id":"inventory",
                "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
                "target_id":"reporting.threshold",
                "effect_ids":["B.t"],
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"],[])

    def test_v6_primitives_still_pass_through(self):
        text="ABC\nEffect targets only: x."
        import hashlib
        out=verify_proof(
            text,
            source_id="doc",
            claims=[{
                "claim_id":"literal",
                "kind":"SOURCE_LITERAL",
                "start":0,
                "end":3,
                "text_sha256":hashlib.sha256(b"ABC").hexdigest(),
            }],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED",out)
        self.assertEqual(out["accepted_claims"][0]["kind"],"SOURCE_LITERAL")


if __name__=="__main__":
    unittest.main()
