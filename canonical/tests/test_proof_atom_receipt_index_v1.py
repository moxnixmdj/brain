from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime.canonical_proof_atom_basis_v1 import atom_id, compile_basis
from canonical.runtime.proof_atom_receipt_index_v1 import index_receipts

ROOT = Path(__file__).resolve().parents[2]


def basis_for(prop="ATOM_X"):
    return {
        "status": "PASS__SYNTHETIC",
        "atoms": [{
            "atom_id": atom_id(prop),
            "proposition": prop,
            "layers": ["TEST"],
            "certificate_ids": ["C"],
            "associated_target_predicates": ["T"],
        }],
    }


def write_json(root: Path, rel: str, doc) -> bytes:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(doc, indent=2) + "\n").encode()
    p.write_bytes(data)
    return data


class Tests(unittest.TestCase):
    def test_exact_mention_is_candidate_not_proof(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            data = write_json(root, "canonical/verification/r.json", {
                "schema": "R",
                "status": "INDEPENDENT_PUBLIC_RUNNER_PASS__ZERO_CREDIT",
                "note": "ATOM_X",
            })
            out = index_receipts(root, basis_for(), scan_prefixes=["canonical/verification"], excluded_paths=frozenset())
            row = out["atom_rows"][0]
            self.assertEqual(row["candidate_receipt_count"], 1)
            self.assertEqual(row["explicit_verified_binding_candidate_count"], 0)
            self.assertEqual(row["candidate_receipts"][0]["git_blob_sha"], hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest())

    def test_explicit_verified_proposition_is_binding_candidate(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            write_json(root, "canonical/verification/r.json", {
                "schema": "R",
                "status": "INDEPENDENT_PUBLIC_RUNNER_PASS__ZERO_CREDIT",
                "verified_propositions": ["ATOM_X"],
            })
            out = index_receipts(root, basis_for(), scan_prefixes=["canonical/verification"], excluded_paths=frozenset())
            row = out["atom_rows"][0]
            self.assertEqual(row["explicit_verified_binding_candidate_count"], 1)
            self.assertEqual(row["index_state"], "EXPLICIT_VERIFIED_BINDING_CANDIDATE_PRESENT")

    def test_failed_receipt_does_not_bind(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            write_json(root, "canonical/verification/r.json", {
                "schema": "R",
                "status": "FAIL",
                "verified_propositions": ["ATOM_X"],
            })
            out = index_receipts(root, basis_for(), scan_prefixes=["canonical/verification"], excluded_paths=frozenset())
            self.assertEqual(out["atom_rows"][0]["explicit_verified_binding_candidate_count"], 0)

    def test_exclusion_prevents_self_proof_noise(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            rel = "canonical/governance/frontier.json"
            write_json(root, rel, {"requires": ["ATOM_X"]})
            out = index_receipts(root, basis_for(), scan_prefixes=["canonical/governance"], excluded_paths=frozenset({rel}))
            self.assertEqual(out["atom_rows"][0]["candidate_receipt_count"], 0)

    def test_live_basis_is_40_atoms_and_index_zero_credit(self):
        global_frontier = json.loads((ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text())
        matched = json.loads((ROOT / "canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json").read_text())
        basis = compile_basis(global_frontier, matched)
        self.assertEqual(basis["leaf_atom_count"], 40)
        out = index_receipts(ROOT, basis)
        self.assertTrue(out["status"].startswith("PASS"), out.get("errors"))
        self.assertEqual(out["leaf_atom_count"], 40)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
