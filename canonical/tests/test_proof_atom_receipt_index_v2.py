from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.proof_atom_receipt_index_v2 import build_index


def frontier():
    return {
        "unresolved_predicates": ["T1","T2"],
        "certificates": [
            {
                "id": "P",
                "target_predicates": ["T1","T2"],
                "requires": ["R1","R2"],
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
                "source_blob_sha": "0"*40,
                "children": [
                    {"id":"C1","target_predicates":["T1"],"requires":["R1"]},
                    {"id":"C2","target_predicates":["T2"],"requires":["R2"]},
                ],
            }
        ]
    }


class Tests(unittest.TestCase):
    def test_exact_candidate_match_is_content_addressed_and_target_specific(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"canonical/verification/r.json"
            p.parent.mkdir(parents=True)
            content='{"claim":"R1"}\n'
            p.write_text(content,encoding="utf-8")
            out=build_index(frontier(),overlay(),root=root)
            self.assertTrue(out["status"].startswith("PASS"),out)
            row=next(x for x in out["atoms"] if x["proposition"]=="R1")
            self.assertEqual(row["associated_target_predicates"],["T1"])
            self.assertEqual(row["candidate_match_count"],1)
            self.assertTrue(row["atom_id"].startswith("PA1:"))
            expected=hashlib.sha1(f"blob {len(content.encode())}\0".encode()+content.encode()).hexdigest()
            self.assertEqual(row["candidate_matches"][0]["git_blob_sha"],expected)

    def test_refinement_overlay_restatement_is_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json"
            p.parent.mkdir(parents=True)
            p.write_text('{"requires":["R1"]}\n',encoding="utf-8")
            out=build_index(frontier(),overlay(),root=root)
            row=next(x for x in out["atoms"] if x["proposition"]=="R1")
            self.assertEqual(row["candidate_match_count"],0)

    def test_semantically_unrelated_substring_does_not_match(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"canonical/verification/r.json"
            p.parent.mkdir(parents=True)
            p.write_text('{"claim":"R"}\n',encoding="utf-8")
            out=build_index(frontier(),overlay(),root=root)
            row=next(x for x in out["atoms"] if x["proposition"]=="R1")
            self.assertEqual(row["candidate_match_count"],0)

    def test_no_credit_or_authority(self):
        with tempfile.TemporaryDirectory() as td:
            out=build_index(frontier(),overlay(),root=Path(td))
            self.assertEqual(out["capability_credit_delta"],0)
            self.assertEqual(out["family_credit_delta"],0)
            self.assertFalse(out["execution_authority"])
            self.assertFalse(out["promotion_authority"])

    def test_live_basis_is_40_pa1_atoms(self):
        root=Path(__file__).resolve().parents[2]
        f=json.loads((root/"canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text())
        o=json.loads((root/"canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text())
        with tempfile.TemporaryDirectory() as td:
            out=build_index(f,o,root=Path(td))
        self.assertEqual(out["canonical_atom_count"],40)
        self.assertTrue(all(x["atom_id"].startswith("PA1:") for x in out["atoms"]))
        by={x["proposition"]:x for x in out["atoms"]}
        self.assertEqual(by["FRONTIERCODE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS"]["associated_target_predicates"],["CODING_FRONTIERCODE_GE_54_4"])
        self.assertEqual(by["ARTIFACT_AA_BRIEFCASE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS"]["associated_target_predicates"],["ARTIFACT_AA_BRIEFCASE_GE_1822"])


if __name__=="__main__":
    unittest.main(verbosity=2)
