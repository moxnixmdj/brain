from __future__ import annotations

import json
import unittest

from canonical.runtime.source_explicit_semantic_claim_autofill_v1 import (
    synthesize_missing_claims,
)
from canonical.runtime.source_aligned_semantic_proof_v8 import verify_proof


def _effect(eid="A.t", value="10", target="threshold"):
    return {
        "conditions": {},
        "effect_class": "DEFINE",
        "effect_id": eid,
        "supersedes": [],
        "target_id": target,
        "valid_from": None,
        "valid_until": None,
        "value": value,
    }


def _relation(effect):
    return "Effect relation: " + json.dumps(
        effect, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


class SourceExplicitSemanticClaimAutofillV1Tests(unittest.TestCase):
    def test_empty_claims_compile_all_explicit_v7_v8_primitives(self):
        effect = _effect()
        source = "\n".join([
            "Effect targets only: threshold.",
            "Effect IDs only for threshold: A.t.",
            _relation(effect),
        ])
        out = synthesize_missing_claims(
            source, source_id="A", existing_claims=[]
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["synthesized_claim_count"], 3)
        kinds = [row["kind"] for row in out["synthesized_claims"]]
        self.assertEqual(
            kinds,
            [
                "CERTIFIED_EFFECT_TARGET_SCOPE",
                "CERTIFIED_EFFECT_ID_INVENTORY",
                "CERTIFIED_DOCUMENT_EFFECT_RELATION",
            ],
        )
        checked = verify_proof(
            source,
            source_id="A",
            claims=out["synthesized_claims"],
        )
        self.assertEqual(checked["status"], "PROOF_CHECKED", checked)
        self.assertEqual(len(checked["accepted_claims"]), 3)

    def test_existing_wrong_relation_owns_slot_and_is_not_replaced(self):
        effect = _effect()
        source = "\n".join([
            "Effect IDs only for threshold: A.t.",
            _relation(effect),
        ])
        wrong = dict(effect)
        wrong["value"] = "99"
        existing = [{
            "claim_id": "caller.wrong",
            "kind": "CERTIFIED_DOCUMENT_EFFECT_RELATION",
            "effect": wrong,
        }]
        out = synthesize_missing_claims(
            source, source_id="A", existing_claims=existing
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(any(
            row["kind"] == "CERTIFIED_DOCUMENT_EFFECT_RELATION"
            for row in out["synthesized_claims"]
        ))
        checked = verify_proof(
            source,
            source_id="A",
            claims=existing + out["synthesized_claims"],
        )
        self.assertTrue(any(
            row.get("claim_id") == "caller.wrong"
            for row in checked["rejected_claims"]
        ))
        self.assertFalse(any(
            row.get("kind") == "CERTIFIED_DOCUMENT_EFFECT_RELATION"
            for row in checked["accepted_claims"]
        ))

    def test_partial_existing_inventory_fills_only_other_slots(self):
        effect = _effect()
        source = "\n".join([
            "Effect targets only: threshold.",
            "Effect IDs only for threshold: A.t.",
            _relation(effect),
        ])
        existing = [{
            "claim_id": "caller.inventory",
            "kind": "CERTIFIED_EFFECT_ID_INVENTORY",
            "target_id": "threshold",
            "effect_ids": ["A.t"],
        }]
        out = synthesize_missing_claims(
            source, source_id="A", existing_claims=existing
        )
        self.assertTrue(out["pass"], out)
        kinds = [row["kind"] for row in out["synthesized_claims"]]
        self.assertIn("CERTIFIED_EFFECT_TARGET_SCOPE", kinds)
        self.assertIn("CERTIFIED_DOCUMENT_EFFECT_RELATION", kinds)
        self.assertNotIn("CERTIFIED_EFFECT_ID_INVENTORY", kinds)

    def test_malformed_existing_inventory_blocks_inventory_autofill(self):
        source = "Effect IDs only for threshold: A.t."
        existing = [{
            "claim_id": "caller.malformed",
            "kind": "CERTIFIED_EFFECT_ID_INVENTORY",
            "effect_ids": ["A.t"],
        }]
        out = synthesize_missing_claims(
            source, source_id="A", existing_claims=existing
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(any(
            row["kind"] == "CERTIFIED_EFFECT_ID_INVENTORY"
            for row in out["synthesized_claims"]
        ))

    def test_unstructured_prose_does_not_create_semantic_claims(self):
        out = synthesize_missing_claims(
            "The threshold might change.",
            source_id="A",
            existing_claims=[],
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["synthesized_claims"], [])
        self.assertFalse(out["semantic_truth_authority"])


if __name__ == "__main__":
    unittest.main()
