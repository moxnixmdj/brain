from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.post_delegation_v4_index_adapter_v1 import (
    current_frontier_projection,build_current_index
)

ROOT=Path(__file__).resolve().parents[2]

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frontier=json.loads((ROOT/"canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text())
        cls.hyper=json.loads((ROOT/"canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json").read_text())
        cls.overlay=json.loads((ROOT/"canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text())

    def test_current_projection_is_30_predicates_39_atoms(self):
        out=current_frontier_projection(self.frontier,self.hyper,self.overlay)
        self.assertTrue(out["status"].startswith("PASS"))
        self.assertEqual(len(out["frontier_projection"]["unresolved_predicates"]),30)
        self.assertEqual(out["proof_atom_basis"]["leaf_atom_count"],39)
        self.assertEqual(out["proof_atom_basis"]["leaf_requirement_occurrence_count"],39)
        self.assertEqual(out["proof_atom_basis"]["exact_duplicate_savings"],0)

    def test_delegation_atom_absent(self):
        out=current_frontier_projection(self.frontier,self.hyper,self.overlay)
        props={x["proposition"] for x in out["proof_atom_basis"]["atoms"]}
        self.assertNotIn(
          "INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_DELEGATION_PROTOCOL",
          props
        )

    def test_v4_scan_uses_39_atom_basis(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for rel in ("canonical/verification","canonical/capabilities","canonical/governance"):
                (root/rel).mkdir(parents=True,exist_ok=True)
            (root/"canonical/verification/EMPTY.txt").write_text("no candidate proposition here",encoding="utf-8")
            out=build_current_index(self.frontier,self.hyper,self.overlay,root=root)
            self.assertTrue(out["status"].startswith("PASS"))
            self.assertEqual(out["v4_index"]["canonical_atom_count"],39)
            self.assertEqual(out["v4_index"]["scanned_file_count"],1)

    def test_fails_closed_if_delegation_missing_before_recompile(self):
        f=json.loads(json.dumps(self.frontier))
        f["unresolved_predicates"].remove("DELEGATION_TERMINAL_SUCCESS_NONINFERIOR")
        self.assertFalse(current_frontier_projection(f,self.hyper,self.overlay)["status"].startswith("PASS"))

    def test_zero_authority(self):
        out=current_frontier_projection(self.frontier,self.hyper,self.overlay)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
