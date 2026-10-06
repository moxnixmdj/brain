from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from canonical.runtime.current_30_terminal_authority_verifier import Authority30Error,verify

ROOT=Path(__file__).resolve().parents[2]
def load(path): return json.loads((ROOT/path).read_text())
def docs():
    return (
      load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
      load("canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json"),
      load("canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V3.json"),
      load("canonical/verification/TERMINAL_30_OBLIGATION_BASIS_SPRITE_VERIFICATION_20261006_V1.json"),
    )

class Current30AuthorityTests(unittest.TestCase):
    def test_current_passes(self):
        out=verify(*docs())
        self.assertEqual(out["open_truth_obligations"],30)
        self.assertFalse(out["terminal"])
    def test_authority_count_drift_fails(self):
        a,p,c,r=docs(); x=copy.deepcopy(a); x["current_routing"]["truth_obligations_preserved"]=31
        with self.assertRaises(Authority30Error): verify(x,p,c,r)
    def test_pointer_route_drift_fails(self):
        a,p,c,r=docs(); x=copy.deepcopy(p); x["terminal_falsification_control_loop"]["route_counts"]["D"]=16
        with self.assertRaises(Authority30Error): verify(a,x,c,r)
    def test_alias_drop_fails(self):
        a,p,c,r=docs(); x=copy.deepcopy(c); del x["family_truth_aliases"]["ARTIFACT_CREATION"]
        with self.assertRaises(Authority30Error): verify(a,p,x,r)
    def test_terminal_promotion_fails(self):
        a,p,c,r=docs(); x=copy.deepcopy(a); x["truth"]["achieved"]=True
        with self.assertRaises(Authority30Error): verify(x,p,c,r)
    def test_deleted_truth_reentry_fails(self):
        a,p,c,r=docs(); x=copy.deepcopy(c); x["truth_repairs"]=x["truth_repairs"][:1]
        with self.assertRaises(Authority30Error): verify(a,p,x,r)

if __name__=="__main__": unittest.main(verbosity=2)
