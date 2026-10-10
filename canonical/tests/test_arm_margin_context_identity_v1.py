from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import arm_margin_context_identity_v1 as arm

ROOT = Path(__file__).resolve().parents[2]


def fake_projection(pack):
    return {
        "pass": True,
        "receipt": {
            "fragment_ids": sorted(
                str(x["fragment_id"]) for x in pack.get("fragments", [])
            ),
            "receipt_sha256": "a" * 64,
        },
        "source_fragment_authority": True,
        "terminal_authority": False,
    }


class Tests(unittest.TestCase):
    def resolve(self, text, target="margin", occurrence=0, verifier=fake_projection):
        starts = []
        pos = 0
        low = text.casefold()
        while True:
            i = low.find(target.casefold(), pos)
            if i < 0:
                break
            starts.append(i)
            pos = i + len(target)
        start = starts[occurrence]
        return arm.resolve_occurrence(
            text,
            start=start,
            end=start + len(target),
            repo_root=ROOT,
            projection_verifier=verifier,
        )

    def test_arm_possessive_margin_with_index_resolves(self):
        out = self.resolve(
            "The ARM's margin increased while the index was unchanged."
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["concept_id"], arm.CONCEPT_ID)
        self.assertTrue(out["occurrence_identity_authority"])
        self.assertFalse(out["bare_margin_sense_authority"])
        self.assertFalse(out["fibo_identity_authority"])

    def test_adjustable_rate_mortgage_margin_added_to_index_resolves(self):
        text = (
            "For the adjustable-rate mortgage, the margin is added to the index "
            "to determine the interest rate."
        )
        out = self.resolve(text)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["concept_id"], arm.CONCEPT_ID)

    def test_index_plus_margin_with_arm_context_resolves(self):
        text = "For this ARM, the index plus the margin determines the rate."
        out = self.resolve(text)
        self.assertTrue(out["pass"], out)

    def test_bare_margin_unresolved(self):
        out = self.resolve("Margin increased.")
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__ARM_AND_INDEX_CONTEXT_REQUIRED",
        )

    def test_index_without_arm_unresolved(self):
        out = self.resolve(
            "The margin was added to the index to determine the rate."
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__ARM_AND_INDEX_CONTEXT_REQUIRED",
        )

    def test_arm_without_index_unresolved(self):
        out = self.resolve("The ARM's margin increased.")
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__ARM_AND_INDEX_CONTEXT_REQUIRED",
        )

    def test_unrelated_margin_in_same_sentence_not_stolen(self):
        text = (
            "The ARM's margin and index were recorded, while gross margin increased."
        )
        out = self.resolve(text, occurrence=1)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__MARGIN_OCCURRENCE_NOT_RELATIONALLY_BOUND_TO_ARM_INDEX",
        )

    def test_negated_local_relation_is_unresolved(self):
        text = (
            "For this ARM, the margin is not added to the index under this test."
        )
        out = self.resolve(text)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NEGATED_OR_NEGATIVE_LOCAL_CONTEXT",
        )

    def test_target_span_must_be_margin(self):
        text = "For this ARM, the index plus the margin determines the rate."
        start = text.index("index")
        out = arm.resolve_occurrence(
            text,
            start=start,
            end=start + len("index"),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__TARGET_OCCURRENCE_IS_NOT_MARGIN",
        )

    def test_source_authentication_failure_fails_closed(self):
        out = self.resolve(
            "The ARM's margin increased while the index was unchanged.",
            verifier=lambda _pack: {"pass": False},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "PINNED_FED_ARM_MARGIN_SOURCE_AUTHORITY_FAILED",
        )

    def test_missing_fragment_fails_closed(self):
        out = self.resolve(
            "The ARM's margin increased while the index was unchanged.",
            verifier=lambda _pack: {
                "pass": True,
                "receipt": {"fragment_ids": [], "receipt_sha256": "b" * 64},
            },
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "FED_ARM_MARGIN_FRAGMENT_NOT_AUTHENTICATED",
        )

    def test_pack_blob_drift_fails_closed(self):
        source = ROOT / arm.PACK_PATH
        doc = json.loads(source.read_text(encoding="utf-8"))
        doc["scope_id"] += "-tampered"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / arm.PACK_PATH
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(doc, sort_keys=True), encoding="utf-8")
            text = "The ARM's margin increased while the index was unchanged."
            start = text.index("margin")
            out = arm.resolve_occurrence(
                text,
                start=start,
                end=start + len("margin"),
                repo_root=root,
                projection_verifier=fake_projection,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("PACK_GIT_BLOB_DRIFT", out["reason"])

    def test_no_global_or_terminal_authority(self):
        out = self.resolve(
            "The ARM's margin increased while the index was unchanged."
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["bare_margin_sense_authority"])
        self.assertFalse(out["fibo_identity_authority"])
        self.assertFalse(out["open_world_finance_semantics_complete"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
