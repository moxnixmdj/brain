import copy,json,unittest
from pathlib import Path
from canonical.runtime.p1_minimum_reality_cut_verifier_v1 import evaluate
ROOT=Path(__file__).resolve().parents[2]
BASE=json.loads((ROOT/"canonical/governance/P1_MINIMUM_REALITY_CUT_INPUT_V1.json").read_text())

class Tests(unittest.TestCase):
    def test_live_exact_cut_is_one_shared_batch(self):
        out=evaluate(copy.deepcopy(BASE))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["minimum_new_reality_units"],1)
        self.assertEqual(out["selected_observation"],"P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH")
    def test_missing_surface_coverage_fails(self):
        d=copy.deepcopy(BASE)
        d["observations"][0]["covers"]=d["observations"][0]["covers"][:-1]
        out=evaluate(d)
        self.assertFalse(out["pass"])
    def test_nonzero_spend_fails(self):
        d=copy.deepcopy(BASE); d["incremental_spend_usd"]=1
        self.assertFalse(evaluate(d)["pass"])
    def test_premature_authority_fails(self):
        d=copy.deepcopy(BASE); d["execution_authority"]=True
        self.assertFalse(evaluate(d)["pass"])

if __name__=="__main__": unittest.main(verbosity=2)
