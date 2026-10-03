from __future__ import annotations
import json
import unittest
from pathlib import Path
from canonical.runtime.post_delegation_frontier_recompile_v1 import (
    compile_post_delegation,TARGET,CERT_ID,ACTION_ID
)

ROOT=Path(__file__).resolve().parents[2]

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frontier=json.loads((ROOT/"canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text())
        cls.hyper=json.loads((ROOT/"canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json").read_text())
        cls.overlay=json.loads((ROOT/"canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text())

    def test_exact_current_recompile(self):
        out=compile_post_delegation(self.frontier,self.hyper,self.overlay)
        self.assertTrue(out["status"].startswith("PASS"))
        self.assertEqual(out["before"],{"unresolved_predicates":31,"certificates":17,"actions":22})
        self.assertEqual(out["after"]["unresolved_predicates"],30)
        self.assertEqual(out["after"]["certificates"],16)
        self.assertEqual(out["after"]["actions"],21)
        self.assertEqual(out["after"]["leaf_requirement_occurrences"],39)
        self.assertEqual(out["after"]["canonical_leaf_atoms"],39)
        self.assertEqual(out["after"]["exact_duplicate_savings"],0)
        self.assertNotIn(TARGET,out["frontier_projection"]["unresolved_predicates"])
        self.assertFalse(any(c["id"]==CERT_ID for c in out["frontier_projection"]["certificates"]))
        self.assertFalse(any(a["id"]==ACTION_ID for a in out["hypergraph_projection"]["actions"]))

    def test_fails_if_delegation_is_shared_certificate(self):
        f=json.loads(json.dumps(self.frontier))
        c=next(x for x in f["certificates"] if x["id"]==CERT_ID)
        c["target_predicates"].append("ANOTHER_TARGET")
        self.assertFalse(compile_post_delegation(f,self.hyper,self.overlay)["status"].startswith("PASS"))

    def test_fails_if_delegation_is_shared_action(self):
        h=json.loads(json.dumps(self.hyper))
        a=next(x for x in h["actions"] if x["id"]==ACTION_ID)
        a["target_predicates"].append("ANOTHER_TARGET")
        self.assertFalse(compile_post_delegation(self.frontier,h,self.overlay)["status"].startswith("PASS"))

    def test_fails_if_target_already_missing(self):
        f=json.loads(json.dumps(self.frontier))
        f["unresolved_predicates"].remove(TARGET)
        self.assertFalse(compile_post_delegation(f,self.hyper,self.overlay)["status"].startswith("PASS"))

    def test_zero_authority(self):
        out=compile_post_delegation(self.frontier,self.hyper,self.overlay)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
