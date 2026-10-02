from __future__ import annotations

import unittest

from canonical.runtime.proof_dependency_guard import evaluate


class ProofDependencyGuardTests(unittest.TestCase):
    def test_unrelated_change_preserves_proof(self):
        out = evaluate({
            "current_blobs": {"a.py": "A1", "b.py": "B2", "docs.md": "D2"},
            "changed_paths": ["docs.md", "b.py"],
            "receipts": [{
                "proof_id": "P",
                "bound_dependencies": {"a.py": "A1"},
                "transitive_dependency_closure_frozen": True,
            }],
        })
        self.assertEqual(out["valid_proof_ids"], ["P"])
        self.assertEqual(out["invalidated_proofs"], [])
        self.assertEqual(out["unaffected_changed_paths_by_valid_proof"]["P"], ["b.py", "docs.md"])

    def test_bound_dependency_change_invalidates_only_affected_proof(self):
        out = evaluate({
            "current_blobs": {"a.py": "A2", "b.py": "B1"},
            "changed_paths": ["a.py"],
            "receipts": [
                {
                    "proof_id": "A_PROOF",
                    "bound_dependencies": {"a.py": "A1"},
                    "transitive_dependency_closure_frozen": True,
                },
                {
                    "proof_id": "B_PROOF",
                    "bound_dependencies": {"b.py": "B1"},
                    "transitive_dependency_closure_frozen": True,
                },
            ],
        })
        self.assertEqual(out["valid_proof_ids"], ["B_PROOF"])
        self.assertEqual(out["invalidated_proofs"][0]["proof_id"], "A_PROOF")
        self.assertEqual(out["invalidated_proofs"][0]["changed_dependency_paths"], ["a.py"])

    def test_missing_dependency_fails_proof_closed(self):
        out = evaluate({
            "current_blobs": {},
            "receipts": [{
                "proof_id": "P",
                "bound_dependencies": {"missing.py": "X"},
                "transitive_dependency_closure_frozen": True,
            }],
        })
        self.assertEqual(out["valid_proof_ids"], [])
        self.assertEqual(out["invalidated_proofs"][0]["missing_dependency_paths"], ["missing.py"])

    def test_unfrozen_dependency_closure_never_preserves_proof(self):
        out = evaluate({
            "current_blobs": {"a.py": "A1"},
            "receipts": [{
                "proof_id": "P",
                "bound_dependencies": {"a.py": "A1"},
                "transitive_dependency_closure_frozen": False,
            }],
        })
        self.assertEqual(out["invalidated_proofs"][0]["reason"], "DEPENDENCY_CLOSURE_NOT_FROZEN")

    def test_duplicate_proof_id_fails_closed(self):
        receipt = {
            "proof_id": "P",
            "bound_dependencies": {"a.py": "A1"},
            "transitive_dependency_closure_frozen": True,
        }
        out = evaluate({
            "current_blobs": {"a.py": "A1"},
            "receipts": [receipt, dict(receipt)],
        })
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("DUPLICATE_PROOF_ID:P", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
