from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.terminal_condition_restriction_cell_compiler_v2 import (
    ConditionRestrictionError,
    canonical_claim_sha256,
    compile_condition_cells,
    git_blob_sha_bytes,
    verify_repo_blob,
)


MATRIX = {
    "shared_condition_matrix": [
        {"condition": "CYBERSECURITY", "mapped_family_union": ["CODING", "AGENCY"]},
        {"condition": "LONG_CONTEXT", "mapped_family_union": ["CODING"]},
    ]
}


class ConditionRestrictionCompilerV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.verification_dir = self.root / "canonical" / "verification"
        self.verification_dir.mkdir(parents=True)

        self.source_path = "canonical/verification/source.json"
        self.source_bytes = b'{"verified_source":true}\n'
        (self.root / self.source_path).write_bytes(self.source_bytes)
        self.source_sha = git_blob_sha_bytes(self.source_bytes)

    def tearDown(self):
        self.tmp.cleanup()

    def write_json_blob(self, rel: str, obj: dict) -> tuple[str, str]:
        data = (json.dumps(obj, sort_keys=True, indent=2) + "\n").encode("utf-8")
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return rel, git_blob_sha_bytes(data)

    def make_claim(self, **overrides):
        claim = {
            "family": "CODING",
            "proof_class": "POINTWISE_UNIVERSAL",
            "covered_conditions": ["CYBERSECURITY"],
            "scope_complete": True,
            "source_path": self.source_path,
            "source_sha": self.source_sha,
        }
        claim.update(overrides)
        return claim

    def make_bound_receipt(
        self,
        *,
        proof_id="p1",
        claim=None,
        attestation_claim_binding=None,
        attestation_subject=None,
        attestation_verdict="PASS",
        attestation_mode="INDEPENDENT_EXTERNAL_RECOMPUTATION",
    ):
        claim = claim or self.make_claim()
        binding = canonical_claim_sha256(claim)
        if attestation_claim_binding is None:
            attestation_claim_binding = binding
        if attestation_subject is None:
            attestation_subject = {
                "path": claim["source_path"],
                "git_blob_sha": claim["source_sha"],
            }
        attestation = {
            "condition_restriction_verdict": attestation_verdict,
            "condition_restriction_attestation_mode": attestation_mode,
            "condition_restriction_claim_binding_sha256": attestation_claim_binding,
            "condition_restriction_subject": attestation_subject,
        }
        att_path, att_sha = self.write_json_blob(
            f"canonical/verification/{proof_id}_attestation.json",
            attestation,
        )
        receipt = {
            "schema": "PROJECT_BRAIN_CONDITION_RESTRICTION_PROOF_RECEIPT_V1",
            "proof_id": proof_id,
            "claim": claim,
            "claim_binding_sha256": binding,
            "attestation_path": att_path,
            "attestation_sha": att_sha,
        }
        receipt_path, receipt_sha = self.write_json_blob(
            f"canonical/verification/{proof_id}_receipt.json",
            receipt,
        )
        return {
            "receipt_path": receipt_path,
            "receipt_sha": receipt_sha,
        }

    def test_exact_attested_receipt_closes_only_bound_cell(self):
        entry = self.make_bound_receipt()
        r = compile_condition_cells(MATRIX, [entry], self.root)
        self.assertEqual(r["closed_cells"], 1)
        self.assertEqual(r["open_cells"], 2)
        closed = [x for x in r["cells"] if x["state"].startswith("CLOSED")]
        self.assertEqual(closed[0]["condition"], "CYBERSECURITY")
        self.assertEqual(closed[0]["family"], "CODING")

    def test_shadow_metadata_in_inventory_is_rejected(self):
        entry = self.make_bound_receipt()
        entry["family"] = "AGENCY"
        entry["covered_conditions"] = ["LONG_CONTEXT"]
        r = compile_condition_cells(MATRIX, [entry], self.root)
        self.assertEqual(r["closed_cells"], 0)
        self.assertEqual(
            r["receipt_rejections"][0]["reason"],
            "INVENTORY_ENTRY_FIELD_SET_INVALID",
        )

    def test_unrelated_valid_blob_plus_forged_metadata_cannot_close(self):
        claim = self.make_claim()
        forged_binding = canonical_claim_sha256({
            **claim,
            "family": "AGENCY",
        })
        entry = self.make_bound_receipt(
            claim=claim,
            attestation_claim_binding=forged_binding,
        )
        r = compile_condition_cells(MATRIX, [entry], self.root)
        self.assertEqual(r["closed_cells"], 0)
        self.assertEqual(
            r["receipt_rejections"][0]["reason"],
            "ATTESTATION_CLAIM_BINDING_MISMATCH",
        )

    def test_attestation_subject_must_bind_exact_source(self):
        entry = self.make_bound_receipt(
            attestation_subject={
                "path": self.source_path,
                "git_blob_sha": "1" * 40,
            }
        )
        r = compile_condition_cells(MATRIX, [entry], self.root)
        self.assertEqual(r["closed_cells"], 0)
        self.assertEqual(
            r["receipt_rejections"][0]["reason"],
            "ATTESTATION_SUBJECT_SHA_MISMATCH",
        )

    def test_attestation_must_pass(self):
        entry = self.make_bound_receipt(attestation_verdict="FAIL")
        r = compile_condition_cells(MATRIX, [entry], self.root)
        self.assertEqual(r["closed_cells"], 0)
        self.assertEqual(
            r["receipt_rejections"][0]["reason"],
            "ATTESTATION_VERDICT_NOT_PASS",
        )

    def test_attestation_mode_is_not_free_form(self):
        entry = self.make_bound_receipt(attestation_mode="SELF_ASSERTED")
        r = compile_condition_cells(MATRIX, [entry], self.root)
        self.assertEqual(r["closed_cells"], 0)
        self.assertEqual(
            r["receipt_rejections"][0]["reason"],
            "ATTESTATION_MODE_NOT_ADMISSIBLE",
        )

    def test_scope_incomplete_claim_stays_open(self):
        entry = self.make_bound_receipt(claim=self.make_claim(scope_complete=False))
        r = compile_condition_cells(MATRIX, [entry], self.root)
        self.assertEqual(r["closed_cells"], 0)
        self.assertEqual(
            r["receipt_rejections"][0]["reason"],
            "SCOPE_INCOMPLETE",
        )

    def test_aggregate_proof_class_stays_open(self):
        entry = self.make_bound_receipt(
            claim=self.make_claim(proof_class="AGGREGATE_MEAN")
        )
        r = compile_condition_cells(MATRIX, [entry], self.root)
        self.assertEqual(r["closed_cells"], 0)
        self.assertEqual(
            r["receipt_rejections"][0]["reason"],
            "PROOF_CLASS_NOT_ADMISSIBLE",
        )

    def test_receipt_mutation_breaks_inventory_binding(self):
        entry = self.make_bound_receipt()
        receipt_file = self.root / entry["receipt_path"]
        obj = json.loads(receipt_file.read_text(encoding="utf-8"))
        obj["proof_id"] = "mutated"
        receipt_file.write_text(json.dumps(obj), encoding="utf-8")
        r = compile_condition_cells(MATRIX, [entry], self.root)
        self.assertEqual(r["closed_cells"], 0)
        self.assertEqual(
            r["receipt_rejections"][0]["reason"],
            "RECEIPT_BLOB_IDENTITY_MISMATCH_OR_UNREADABLE",
        )

    def test_source_mutation_breaks_claim(self):
        entry = self.make_bound_receipt()
        (self.root / self.source_path).write_text(
            '{"verified_source":false}\n',
            encoding="utf-8",
        )
        r = compile_condition_cells(MATRIX, [entry], self.root)
        self.assertEqual(r["closed_cells"], 0)
        self.assertEqual(
            r["receipt_rejections"][0]["reason"],
            "SOURCE_BLOB_IDENTITY_MISMATCH_OR_UNREADABLE",
        )

    def test_attestation_mutation_breaks_receipt(self):
        entry = self.make_bound_receipt()
        receipt = json.loads(
            (self.root / entry["receipt_path"]).read_text(encoding="utf-8")
        )
        att_file = self.root / receipt["attestation_path"]
        att_file.write_text('{"condition_restriction_verdict":"PASS"}\n', encoding="utf-8")
        r = compile_condition_cells(MATRIX, [entry], self.root)
        self.assertEqual(r["closed_cells"], 0)
        self.assertEqual(
            r["receipt_rejections"][0]["reason"],
            "ATTESTATION_BLOB_IDENTITY_MISMATCH_OR_UNREADABLE",
        )

    def test_claim_field_set_is_exact(self):
        claim = self.make_claim()
        claim["independent_or_objective"] = True
        entry = self.make_bound_receipt(claim=claim)
        r = compile_condition_cells(MATRIX, [entry], self.root)
        self.assertEqual(r["closed_cells"], 0)
        self.assertEqual(
            r["receipt_rejections"][0]["reason"],
            "CLAIM_FIELD_SET_INVALID",
        )

    def test_objective_ceiling_with_objective_attestation_can_close(self):
        entry = self.make_bound_receipt(
            claim=self.make_claim(proof_class="OBJECTIVE_CEILING"),
            attestation_mode="OBJECTIVE_FORMAL_VERIFICATION",
        )
        r = compile_condition_cells(MATRIX, [entry], self.root)
        self.assertEqual(r["closed_cells"], 1)

    def test_exhaustive_per_case_with_independent_attestation_can_close(self):
        entry = self.make_bound_receipt(
            claim=self.make_claim(proof_class="EXHAUSTIVE_FINITE_PER_CASE"),
        )
        r = compile_condition_cells(MATRIX, [entry], self.root)
        self.assertEqual(r["closed_cells"], 1)

    def test_actual_blob_verifier_detects_mutation(self):
        self.assertTrue(
            verify_repo_blob(self.root, self.source_path, self.source_sha)
        )
        (self.root / self.source_path).write_text(
            '{"verified_source":false}\n',
            encoding="utf-8",
        )
        self.assertFalse(
            verify_repo_blob(self.root, self.source_path, self.source_sha)
        )

    def test_missing_matrix_fails_closed(self):
        entry = self.make_bound_receipt()
        with self.assertRaises(ConditionRestrictionError):
            compile_condition_cells({}, [entry], self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
