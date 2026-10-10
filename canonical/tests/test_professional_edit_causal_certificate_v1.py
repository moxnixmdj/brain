from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_edit_causal_certificate_v1 as c

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = (
    ROOT
    / "canonical/verification/"
    / "PROFESSIONAL_QUALITY_R7_SINGLE_EDIT_CAUSAL_INSTANCE_VERIFY_20261009_V1.json"
)


def source_receipt():
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


class ProfessionalEditCausalCertificateV1Tests(unittest.TestCase):
    def test_current_verified_single_edit_compiles_claim_scoped_certificate(self):
        out = c.compile_certificate(source_receipt())
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__EXACT_SINGLE_EDIT_CAUSAL_CERTIFICATE_COMPILED",
        )
        self.assertTrue(out["causal_claim_authority"])
        self.assertTrue(out["reusable_mechanism"])
        self.assertFalse(out["global_r7_authority"])
        self.assertFalse(out["domain_semantic_closure"])
        self.assertFalse(out["domain_execution_closure"])
        self.assertFalse(out["terminal_authority"])

    def test_changed_test_bytes_fail_closed(self):
        row = source_receipt()
        row["real_execution"]["same_test_bytes"] = False
        out = c.compile_certificate(row)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SAME_TEST_BYTES_REQUIRED")

    def test_no_intervention_byte_change_fail_closed(self):
        row = source_receipt()
        same = row["exact_subject"]["predecessor_runtime_git_blob_sha"]
        row["exact_subject"]["repaired_runtime_git_blob_sha"] = same
        row["byte_identity"]["repaired_runtime_materialized_git_hash_object"] = same
        out = c.compile_certificate(row)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "NO_INTERVENTION_BYTE_CHANGE")

    def test_pass_to_pass_is_not_causal_rescue(self):
        row = source_receipt()
        row["real_execution"]["predecessor_result"]["outcome"] = "PASS"
        row["real_execution"]["predecessor_result"]["return_code"] = 0
        out = c.compile_certificate(row)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "REQUIRED_FAIL_TO_PASS_SIGNATURE_MISSING")

    def test_compound_claim_cannot_hide_inside_single_edit_certificate(self):
        row = source_receipt()
        row["r7_defeater_disposition"]["C29_COMPOUND_EDIT_ATTRIBUTION"][
            "claim_scoped_state"
        ] = "DISCHARGED_FOR_THIS_EXACT_INSTANCE"
        out = c.compile_certificate(row)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "R7_DEFEATER_STATE_INVALID:C29_COMPOUND_EDIT_ATTRIBUTION",
        )

    def test_sequence_claim_cannot_hide_inside_single_edit_certificate(self):
        row = source_receipt()
        row["conclusions"]["sequence_invariance_proved"] = True
        out = c.compile_certificate(row)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "SOURCE_OVERCLAIM_FORBIDDEN:sequence_invariance_proved",
        )

    def test_global_r7_overclaim_fails_closed(self):
        row = source_receipt()
        row["conclusions"]["r7_global_root_closed"] = True
        out = c.compile_certificate(row)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "SOURCE_OVERCLAIM_FORBIDDEN:r7_global_root_closed",
        )

    def test_materialized_byte_identity_must_match_subject(self):
        row = source_receipt()
        row["byte_identity"]["repaired_runtime_materialized_git_hash_object"] = "0" * 40
        out = c.compile_certificate(row)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "REPAIRED_BYTE_IDENTITY_MISMATCH")


if __name__ == "__main__":
    unittest.main()
