from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.terminal_condition_restriction_cell_compiler_v2 import (
    ConditionRestrictionError,
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
        src = self.root / "canonical" / "verification" / "x.json"
        src.parent.mkdir(parents=True)
        self.payload = b'{"verified":true}\n'
        src.write_bytes(self.payload)
        self.sha = git_blob_sha_bytes(self.payload)

    def tearDown(self):
        self.tmp.cleanup()

    def proof(self, **overrides):
        p = {
            "proof_id": "p1",
            "family": "CODING",
            "proof_class": "POINTWISE_UNIVERSAL",
            "covered_conditions": ["CYBERSECURITY"],
            "independent_or_objective": True,
            "scope_complete": True,
            "source_path": "canonical/verification/x.json",
            "source_sha": self.sha,
        }
        p.update(overrides)
        return p

    def test_exact_blob_condition_family_pointwise_closes(self):
        r = compile_condition_cells(MATRIX, [self.proof()], self.root)
        self.assertEqual(r["closed_cells"], 1)
        self.assertEqual(r["open_cells"], 2)

    def test_forged_but_well_formed_sha_stays_open(self):
        r = compile_condition_cells(MATRIX, [self.proof(source_sha="1" * 40)], self.root)
        self.assertEqual(r["closed_cells"], 0)
        self.assertEqual(r["receipt_rejections"][0]["reason"], "SOURCE_BLOB_IDENTITY_MISMATCH_OR_UNREADABLE")

    def test_missing_source_stays_open(self):
        r = compile_condition_cells(MATRIX, [self.proof(source_path="canonical/verification/missing.json")], self.root)
        self.assertEqual(r["closed_cells"], 0)

    def test_path_traversal_stays_open(self):
        r = compile_condition_cells(MATRIX, [self.proof(source_path="../outside.json")], self.root)
        self.assertEqual(r["closed_cells"], 0)

    def test_missing_condition_scope_stays_open(self):
        r = compile_condition_cells(MATRIX, [self.proof(covered_conditions=[])], self.root)
        self.assertEqual(r["closed_cells"], 0)

    def test_aggregate_proof_stays_open(self):
        r = compile_condition_cells(MATRIX, [self.proof(proof_class="AGGREGATE_MEAN")], self.root)
        self.assertEqual(r["closed_cells"], 0)

    def test_scope_incomplete_stays_open(self):
        r = compile_condition_cells(MATRIX, [self.proof(scope_complete=False)], self.root)
        self.assertEqual(r["closed_cells"], 0)

    def test_non_independent_stays_open(self):
        r = compile_condition_cells(MATRIX, [self.proof(independent_or_objective=False)], self.root)
        self.assertEqual(r["closed_cells"], 0)

    def test_wrong_family_stays_open(self):
        r = compile_condition_cells(MATRIX, [self.proof(family="OTHER")], self.root)
        self.assertEqual(r["closed_cells"], 0)

    def test_objective_ceiling_exact_blob_can_close(self):
        r = compile_condition_cells(MATRIX, [self.proof(proof_class="OBJECTIVE_CEILING")], self.root)
        self.assertEqual(r["closed_cells"], 1)

    def test_exhaustive_per_case_exact_blob_can_close(self):
        r = compile_condition_cells(MATRIX, [self.proof(proof_class="EXHAUSTIVE_FINITE_PER_CASE")], self.root)
        self.assertEqual(r["closed_cells"], 1)

    def test_actual_blob_verifier_detects_mutation(self):
        self.assertTrue(verify_repo_blob(self.root, "canonical/verification/x.json", self.sha))
        (self.root / "canonical" / "verification" / "x.json").write_text('{"verified":false}\n', encoding="utf-8")
        self.assertFalse(verify_repo_blob(self.root, "canonical/verification/x.json", self.sha))

    def test_invalid_covered_condition_type_rejected(self):
        r = compile_condition_cells(MATRIX, [self.proof(covered_conditions=["CYBERSECURITY", 7])], self.root)
        self.assertEqual(r["closed_cells"], 0)
        self.assertEqual(r["receipt_rejections"][0]["reason"], "COVERED_CONDITIONS_INVALID")

    def test_missing_matrix_fails_closed(self):
        with self.assertRaises(ConditionRestrictionError):
            compile_condition_cells({}, [self.proof()], self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
