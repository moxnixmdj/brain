from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch
import unittest

from canonical.runtime import professional_r12_root_registry_verify_v3 as v


ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/v.REGISTRY_PATH


def registry():
    return json.loads(REG.read_text(encoding="utf-8"))


class Tests(unittest.TestCase):
    def test_exact_registry_is_three_of_three_and_r4_closed(self):
        out=v.verify(repo_root=ROOT)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proved_root_ids"],v.EXPECTED_PROVED)
        self.assertEqual(out["open_root_ids"],[])
        self.assertEqual(out["proved_root_count"],3)
        self.assertEqual(out["open_root_count"],0)
        self.assertTrue(out["r4_proof_closure"])
        self.assertFalse(out["semantic_property_truth_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)

    def test_cc_r3_semantic_receipt_is_load_bearing(self):
        d=registry()
        d["certificate_slots"][2]["independent_verification"]["git_blob_sha"]="0"*40
        out=v.evaluate(d,repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertTrue(
            any(
                "SEMANTIC_ROOT_REPLAY_FAILED:CC_R3_TERMINAL_CLOSURE_V1" in e
                or "INDEPENDENT_VERIFICATION_BLOB_SHA_MISMATCH" in e
                for e in out["errors"]
            ),
            out,
        )

    def test_r4_cannot_be_claimed_with_root_count_drift(self):
        d=registry()
        d["currently_proved_root_certificates"]=2
        d["currently_open_root_certificates"]=1
        out=v.evaluate(d,repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertTrue(
            any(
                "PROVED_COUNT_DRIFT" in e
                or "OPEN_COUNT_DRIFT" in e
                or "PROVED_ROOT_COUNT_DRIFT" in e
                or "OPEN_ROOT_COUNT_DRIFT" in e
                for e in out["errors"]
            ),
            out,
        )

    def test_cross_claim_cc_r3_binding_fails(self):
        d=registry()
        d["certificate_slots"][2]["certificate"]["claim_binding"]["claim_id"]="0"*64
        out=v.evaluate(d,repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertTrue(
            any("PROVED_SLOT_CLAIM_BINDING_MISMATCH:CC_R3_TERMINAL_CLOSURE_V1:claim_id" in e for e in out["errors"]),
            out,
        )

    def test_semantic_replay_failure_reopens_r4(self):
        real=v.validate_semantic_root_slot

        def altered(root,slot,active):
            if slot.get("root_id")=="CC_R3_TERMINAL_CLOSURE_V1":
                return {"pass":False,"status":"FAIL_CLOSED","errors":["SYNTHETIC"]}
            return real(root,slot,active)

        with patch.object(v,"validate_semantic_root_slot",side_effect=altered):
            out=v.verify(repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertIn(
            "SEMANTIC_ROOT_REPLAY_FAILED:CC_R3_TERMINAL_CLOSURE_V1",
            out["errors"],
        )
        self.assertFalse(out["r4_proof_closure"])

    def test_no_remaining_root_or_obligation(self):
        d=registry()
        self.assertIsNone(d["exact_remaining_root"])
        self.assertIsNone(d["exact_remaining_obligation"])
        out=v.evaluate(d,repo_root=ROOT)
        self.assertTrue(out["pass"],out)

    def test_property_truth_does_not_auto_promote_from_r4(self):
        out=v.verify(repo_root=ROOT)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["r4_proof_closure"])
        self.assertFalse(out["semantic_property_truth_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
