from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import nyfed_loss_cushion_ccob_source_identity_v1 as proof
from canonical.runtime.regcap_necessary_property_authority_v1 import CCOB


ROOT = Path(__file__).resolve().parents[2]


def passing_source(gap=160, *, same_anchor=True):
    anchor = "what type of losses"
    return {
        "pass": True,
        "url": "https://www.newyorkfed.org/newsevents/speeches/2010/dud101010",
        "receipt": {"receipt_sha256": "a" * 64},
        "matched_fragments": [
            {
                "fragment_id": proof.IDENTITY_FRAGMENT_ID,
                "fragment_index": 1000,
                "section_anchor": anchor,
            },
            {
                "fragment_id": proof.LOSS_CUSHION_FRAGMENT_ID,
                "fragment_index": 1000 + gap,
                "section_anchor": anchor if same_anchor else "other anchor",
            },
        ],
    }


class Tests(unittest.TestCase):
    def test_exact_source_context_maps_to_ccob_only(self):
        with patch.object(proof, "verify_projection_pack", return_value=passing_source()):
            out = proof.verify(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["mapped_concept_id"], CCOB)
        self.assertTrue(out["source_context_identity_authority"])
        self.assertTrue(out["semantic_identity_authority"])
        self.assertTrue(out["semantic_truth_authority"])
        self.assertFalse(out["global_phrase_identity_authority"])
        self.assertFalse(out["open_world_ontology_complete"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_source_projection_failure_fails_closed(self):
        with patch.object(
            proof,
            "verify_projection_pack",
            return_value={"pass": False, "reason": "SOURCE_FRAGMENT_PROJECTION_NOT_FOUND"},
        ):
            out = proof.verify(repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "SOURCE_PROJECTION_AUTHORITY_FAILED")

    def test_reverse_fragment_order_does_not_map(self):
        with patch.object(
            proof,
            "verify_projection_pack",
            return_value=passing_source(gap=-10),
        ):
            out = proof.verify(repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__SOURCE_FRAGMENTS_NOT_IN_ADMITTED_RELATION_SHAPE",
        )
        self.assertIsNone(out["mapped_concept_id"])

    def test_excessive_fragment_distance_does_not_map(self):
        with patch.object(
            proof,
            "verify_projection_pack",
            return_value=passing_source(gap=proof.MAX_RELATION_GAP_CHARS + 1),
        ):
            out = proof.verify(repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__SOURCE_FRAGMENTS_NOT_IN_ADMITTED_RELATION_SHAPE",
        )

    def test_different_section_anchor_does_not_map(self):
        with patch.object(
            proof,
            "verify_projection_pack",
            return_value=passing_source(same_anchor=False),
        ):
            out = proof.verify(repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__SOURCE_FRAGMENTS_NOT_IN_SAME_AUTHENTICATED_SECTION",
        )

    def test_missing_required_fragment_fails_closed(self):
        source = passing_source()
        source["matched_fragments"] = source["matched_fragments"][:1]
        with patch.object(proof, "verify_projection_pack", return_value=source):
            out = proof.verify(repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "REQUIRED_SOURCE_FRAGMENT_MISSING_FROM_RECEIPT")

    def test_pack_blob_drift_fails_closed(self):
        original = ROOT / proof.PACK_PATH
        doc = json.loads(original.read_text(encoding="utf-8"))
        doc["source_id"] = doc["source_id"] + "_tampered"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / proof.PACK_PATH
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(doc), encoding="utf-8")
            out = proof.verify(repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("PACK_GIT_BLOB_DRIFT", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
