from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.proof_atom_receipt_index_v2 import build_index


def frontier():
    return {
        "unresolved_predicates": ["T"],
        "certificates": [
            {
                "id": "P",
                "target_predicates": ["T"],
                "requires": ["T::SEMANTIC"],
            }
        ],
    }


def overlay():
    return {
        "refinements": [
            {
                "parent_certificate_id": "P",
                "mode": "EXACT_REQUIREMENT_PARTITION",
                "independent_verified": True,
                "verification_receipt": "r://partition",
                "children": [
                    {
                        "id": "T_CERT",
                        "target_predicates": ["T"],
                        "requires": ["T::SEMANTIC"],
                    }
                ],
            }
        ]
    }


class Tests(unittest.TestCase):
    def test_candidate_match_is_content_addressed_and_pa1_stable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/verification/evidence.json"
            p.parent.mkdir(parents=True)
            content = '{"claim":"T::SEMANTIC"}\n'
            p.write_text(content, encoding="utf-8")
            out = build_index(frontier(), overlay(), root=root, source_revision="abc")
            self.assertTrue(out["status"].startswith("PASS"), out)
            self.assertEqual(out["source_revision"], "abc")
            self.assertEqual(out["canonical_atom_count"], 1)
            row = out["atoms"][0]
            self.assertTrue(row["atom_id"].startswith("PA1:"))
            self.assertEqual(row["candidate_match_count"], 1)
            expected = hashlib.sha1(f"blob {len(content.encode())}\0".encode() + content.encode()).hexdigest()
            self.assertEqual(row["candidate_matches"][0]["git_blob_sha"], expected)
            self.assertEqual(row["candidate_matches"][0]["source_class"], "VERIFICATION_RECEIPT")

    def test_structural_definition_is_not_candidate_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json"
            p.parent.mkdir(parents=True)
            p.write_text('{"requires":["T::SEMANTIC"]}\n', encoding="utf-8")
            out = build_index(frontier(), overlay(), root=root)
            self.assertEqual(out["candidate_match_count"], 0)
            self.assertEqual(out["atoms_without_candidate_matches"], 1)

    def test_basis_verification_receipt_is_not_candidate_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/verification/CANONICAL_PROOF_ATOM_BASIS_V2_HARDENED_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
            p.parent.mkdir(parents=True)
            p.write_text('{"mentions":"T::SEMANTIC"}\n', encoding="utf-8")
            out = build_index(frontier(), overlay(), root=root)
            self.assertEqual(out["candidate_match_count"], 0)

    def test_corpus_manifest_changes_when_unmatched_evidence_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/verification/unmatched.json"
            p.parent.mkdir(parents=True)
            p.write_text('{"x":1}\n', encoding="utf-8")
            a = build_index(frontier(), overlay(), root=root)
            p.write_text('{"x":2}\n', encoding="utf-8")
            b = build_index(frontier(), overlay(), root=root)
            self.assertNotEqual(
                a["scanned_corpus_manifest_sha256"],
                b["scanned_corpus_manifest_sha256"],
            )

    def test_result_is_deterministic_for_same_corpus(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/capabilities/e.json"
            p.parent.mkdir(parents=True)
            p.write_text('{"claim":"T::SEMANTIC"}\n', encoding="utf-8")
            a = build_index(frontier(), overlay(), root=root, source_revision="r1")
            b = build_index(frontier(), overlay(), root=root, source_revision="r1")
            self.assertEqual(a["result_payload_sha256"], b["result_payload_sha256"])
            self.assertEqual(a["scanned_corpus_manifest_sha256"], b["scanned_corpus_manifest_sha256"])

    def test_no_credit_or_authority(self):
        with tempfile.TemporaryDirectory() as td:
            out = build_index(frontier(), overlay(), root=Path(td))
            self.assertEqual(out["capability_credit_delta"], 0)
            self.assertEqual(out["family_credit_delta"], 0)
            self.assertFalse(out["execution_authority"])
            self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
