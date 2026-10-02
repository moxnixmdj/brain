from __future__ import annotations
import unittest

from canonical.runtime.freeze_proof_atom_receipt_index_scan_v1 import INPUT_PATHS, freeze


class Tests(unittest.TestCase):
    def test_freeze_binds_exact_scan_identity(self):
        index = {
            "status": "PASS__CONTENT_ADDRESSED_CANDIDATE_RECEIPT_INDEX_COMPUTED__ZERO_CREDIT",
            "canonical_atom_count": 40,
            "atoms": [],
        }
        blobs = {p: "a" * 40 for p in INPUT_PATHS}
        out = freeze(index, scanned_commit_sha="b" * 40, scanned_tree_sha="c" * 40, input_blob_shas=blobs)
        self.assertEqual(out["scanned_commit_sha"], "b" * 40)
        self.assertEqual(out["scanned_tree_sha"], "c" * 40)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])

    def test_rejects_nonpass_index(self):
        with self.assertRaises(ValueError):
            freeze(
                {"status": "FAIL_CLOSED", "canonical_atom_count": 40},
                scanned_commit_sha="b" * 40,
                scanned_tree_sha="c" * 40,
                input_blob_shas={p: "a" * 40 for p in INPUT_PATHS},
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
