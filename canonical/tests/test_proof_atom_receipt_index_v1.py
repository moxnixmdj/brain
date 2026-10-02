from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.proof_atom_receipt_index_v1 import build_index


def frontier():
    return {
        "unresolved_predicates": ["T"],
        "certificates": [
            {
                "id": "MATCHED_SCOPE_BINDING_CERTIFICATE",
                "target_predicates": ["T"],
                "requires": ["COARSE_A", "COARSE_B"],
            }
        ],
    }


def subfrontier():
    return {
        "unresolved_predicates": ["T"],
        "certificates": [
            {
                "id": "T_CERT",
                "target_predicates": ["T"],
                "requires": ["T::SEMANTIC", "T::SCOPE"],
            }
        ],
    }


class Tests(unittest.TestCase):
    def test_exact_candidate_match_is_content_addressed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/verification/r.json"
            p.parent.mkdir(parents=True)
            content = '{"claim":"T::SEMANTIC"}\n'
            p.write_text(content, encoding="utf-8")
            out = build_index(frontier(), subfrontier(), root=root)
            self.assertTrue(out["status"].startswith("PASS"))
            row = next(x for x in out["atoms"] if x["proposition"] == "T::SEMANTIC")
            self.assertEqual(row["candidate_match_count"], 1)
            expected = hashlib.sha1(f"blob {len(content.encode())}\0".encode() + content.encode()).hexdigest()
            self.assertEqual(row["candidate_matches"][0]["git_blob_sha"], expected)
            self.assertEqual(row["candidate_matches"][0]["source_class"], "VERIFICATION_RECEIPT")

    def test_substring_is_not_exact_literal_match(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/verification/r.json"
            p.parent.mkdir(parents=True)
            p.write_text('{"claim":"T::SEMANTI"}\n', encoding="utf-8")
            out = build_index(frontier(), subfrontier(), root=root)
            row = next(x for x in out["atoms"] if x["proposition"] == "T::SEMANTIC")
            self.assertEqual(row["candidate_match_count"], 0)

    def test_definition_restatement_is_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json"
            p.parent.mkdir(parents=True)
            p.write_text('{"requirement":"T::SEMANTIC"}\n', encoding="utf-8")
            out = build_index(frontier(), subfrontier(), root=root)
            row = next(x for x in out["atoms"] if x["proposition"] == "T::SEMANTIC")
            self.assertEqual(row["candidate_match_count"], 0)

    def test_capability_and_governance_classes_are_distinct(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p1 = root / "canonical/capabilities/x.json"
            p2 = root / "canonical/governance/x.json"
            p1.parent.mkdir(parents=True)
            p2.parent.mkdir(parents=True)
            p1.write_text('{"claim":"T::SCOPE"}\n', encoding="utf-8")
            p2.write_text('{"claim":"T::SCOPE"}\n', encoding="utf-8")
            out = build_index(frontier(), subfrontier(), root=root)
            row = next(x for x in out["atoms"] if x["proposition"] == "T::SCOPE")
            self.assertEqual(row["candidate_match_count"], 2)
            classes = sorted(x["source_class"] for x in row["candidate_matches"])
            self.assertEqual(classes, ["CAPABILITY_EVIDENCE", "GOVERNANCE_EVIDENCE_OR_BINDING"])

    def test_no_credit_or_authority(self):
        with tempfile.TemporaryDirectory() as td:
            out = build_index(frontier(), subfrontier(), root=Path(td))
            self.assertEqual(out["capability_credit_delta"], 0)
            self.assertEqual(out["family_credit_delta"], 0)
            self.assertFalse(out["execution_authority"])
            self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
