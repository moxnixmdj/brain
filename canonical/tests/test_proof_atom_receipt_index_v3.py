from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.canonical_proof_atom_basis_v2 import atom_id
from canonical.runtime.proof_atom_receipt_index_v3 import build_index


def frontier():
    return {
        "unresolved_predicates": ["T1", "T2"],
        "certificates": [
            {
                "id": "PARENT",
                "target_predicates": ["T1", "T2"],
                "requires": ["A", "B"],
            }
        ],
    }


def overlay():
    return {
        "refinements": [
            {
                "parent_certificate_id": "PARENT",
                "mode": "EXACT_REQUIREMENT_PARTITION",
                "independent_verified": True,
                "verification_receipt": "fixture",
                "children": [
                    {"id": "C1", "target_predicates": ["T1"], "requires": ["A"]},
                    {"id": "C2", "target_predicates": ["T2"], "requires": ["B"]},
                ],
            }
        ]
    }


class Tests(unittest.TestCase):
    def test_v2_basis_and_pa1_identity_are_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/verification/r.json"
            p.parent.mkdir(parents=True)
            content = '{"claim":"A"}\n'
            p.write_text(content, encoding="utf-8")
            out = build_index(frontier(), overlay(), root=root)
            self.assertTrue(out["status"].startswith("PASS"))
            self.assertEqual(out["canonical_atom_count"], 2)
            row = next(x for x in out["atoms"] if x["proposition"] == "A")
            self.assertEqual(row["atom_id"], atom_id("A"))
            self.assertEqual(row["candidate_match_count"], 1)
            expected = hashlib.sha1(f"blob {len(content.encode())}\0".encode() + content.encode()).hexdigest()
            self.assertEqual(row["candidate_matches"][0]["git_blob_sha"], expected)

    def test_corpus_digest_changes_even_when_unrelated_evidence_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/verification/unrelated.json"
            p.parent.mkdir(parents=True)
            p.write_text('{"x":"one"}\n', encoding="utf-8")
            first = build_index(frontier(), overlay(), root=root)
            p.write_text('{"x":"two"}\n', encoding="utf-8")
            second = build_index(frontier(), overlay(), root=root)
            self.assertEqual(first["candidate_match_count"], 0)
            self.assertEqual(second["candidate_match_count"], 0)
            self.assertNotEqual(
                first["scanned_corpus_manifest_sha256"],
                second["scanned_corpus_manifest_sha256"],
            )
            self.assertNotEqual(first["index_fingerprint_sha256"], second["index_fingerprint_sha256"])

    def test_review_queue_prefers_verification_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            g = root / "canonical/governance/g.json"
            v = root / "canonical/verification/v.json"
            g.parent.mkdir(parents=True)
            v.parent.mkdir(parents=True)
            g.write_text('{"claim":"A"}\n', encoding="utf-8")
            v.write_text('{"claim":"B"}\n', encoding="utf-8")
            out = build_index(frontier(), overlay(), root=root)
            self.assertEqual(out["review_queue_length"], 2)
            self.assertEqual(out["review_queue"][0]["proposition"], "B")
            self.assertEqual(
                out["review_queue"][0]["best_candidate"]["source_class"],
                "VERIFICATION_RECEIPT",
            )

    def test_explicit_pa1_reference_strengthens_priority_within_class(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p1 = root / "canonical/verification/a.json"
            p2 = root / "canonical/verification/b.json"
            p1.parent.mkdir(parents=True)
            p1.write_text('{"claim":"A"}\n', encoding="utf-8")
            p2.write_text('{"claim":"B","atom":"' + atom_id("B") + '"}\n', encoding="utf-8")
            out = build_index(frontier(), overlay(), root=root)
            self.assertEqual(out["review_queue"][0]["proposition"], "B")
            self.assertTrue(out["review_queue"][0]["best_candidate"]["explicit_atom_id_reference"])

    def test_definition_restatement_is_excluded_from_scan_and_digest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = build_index(frontier(), overlay(), root=root)
            p = root / "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json"
            p.parent.mkdir(parents=True)
            p.write_text('{"definition":"A"}\n', encoding="utf-8")
            changed = build_index(frontier(), overlay(), root=root)
            self.assertEqual(base["scanned_file_count"], changed["scanned_file_count"])
            self.assertEqual(
                base["scanned_corpus_manifest_sha256"],
                changed["scanned_corpus_manifest_sha256"],
            )

    def test_identifier_superstring_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/verification/r.json"
            p.parent.mkdir(parents=True)
            p.write_text('{"claim":"A_EXTENDED"}\\n', encoding="utf-8")
            out = build_index(frontier(), overlay(), root=root)
            row = next(x for x in out["atoms"] if x["proposition"] == "A")
            self.assertEqual(row["candidate_match_count"], 0)

    def test_match_cap_never_hides_actual_count(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            d = root / "canonical/verification"
            d.mkdir(parents=True)
            for i in range(65):
                (d / f"r{i:02d}.json").write_text('{"claim":"A"}\\n', encoding="utf-8")
            out = build_index(frontier(), overlay(), root=root)
            row = next(x for x in out["atoms"] if x["proposition"] == "A")
            self.assertEqual(row["candidate_match_count"], 65)
            self.assertEqual(row["stored_candidate_match_count"], 64)
            self.assertTrue(row["candidate_match_truncated"])
            self.assertEqual(out["atoms_with_truncated_candidate_lists"], 1)

    def test_no_credit_or_authority(self):
        with tempfile.TemporaryDirectory() as td:
            out = build_index(frontier(), overlay(), root=Path(td))
            self.assertEqual(out["capability_credit_delta"], 0)
            self.assertEqual(out["family_credit_delta"], 0)
            self.assertEqual(out["new_reality_units_consumed"], 0)
            self.assertFalse(out["execution_authority"])
            self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
