from __future__ import annotations
import json
import unittest
from pathlib import Path

from canonical.runtime.proof_atom_receipt_index_v2 import EXCLUDED_BASENAMES, ROOT, build_index


class Tests(unittest.TestCase):
    def test_live_v2_basis_scan_is_complete_and_zero_credit(self):
        frontier = json.loads((ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text())
        overlay = json.loads((ROOT / "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text())
        out = build_index(frontier, overlay, root=ROOT)
        self.assertTrue(out["status"].startswith("PASS"), out)
        self.assertEqual(out["canonical_atom_count"], 40)
        self.assertEqual(out["proof_atom_basis_schema"], "PROJECT_BRAIN_CANONICAL_PROOF_ATOM_BASIS_V2")
        self.assertFalse(out["bounded_incomplete"])
        self.assertTrue(all(row["atom_id"].startswith("PA1:") for row in out["atoms"]))
        for row in out["atoms"]:
            for match in row["candidate_matches"]:
                self.assertNotIn(Path(match["path"]).name, EXCLUDED_BASENAMES)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
