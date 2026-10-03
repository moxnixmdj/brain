import copy,json,unittest
from pathlib import Path
from canonical.runtime.p1_current_counterexample_residual_reconciliation_v1 import evaluate,blob

ROOT=Path(__file__).resolve().parents[2]
def load(p): return json.loads((ROOT/p).read_text())

class Tests(unittest.TestCase):
    def docs(self):
        return (
          load("canonical/governance/P1_COMPOSITE_PROOF_ROLE_RECONCILIATION_V1.json"),
          load("canonical/governance/P1_COMPOSITE_PROOF_COUNTEREXAMPLE_QUARANTINE_V1.json"),
          load("canonical/verification/P1_COMPOSITE_PROOF_COUNTEREXAMPLE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
          blob(ROOT/"canonical/runtime/trajectory_failure_typed_ir_proof_v4.py"),
        )
    def test_live_reduces_to_one_current_counterexample(self):
        out=evaluate(*self.docs())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["current_applicable_counterexample_count"],1)
        self.assertEqual(out["stale_counterexample_count"],1)
        self.assertFalse(out["whole_p1_contract_restored"])
    def test_reassigning_unfalsifiable_back_to_terminal_fails_closed(self):
        recon,q,r,v=self.docs()
        recon=copy.deepcopy(recon)
        recon["mutation_roles"]["V4_TYPED_CROSS_DOMAIN_PREFLIGHT"].remove("UNFALSIFIABLE_DIAGNOSIS")
        recon["mutation_roles"]["T0_T2_TERMINAL_INTERVENTION_RESCUE"].append("UNFALSIFIABLE_DIAGNOSIS")
        out=evaluate(recon,q,r,v)
        self.assertFalse(out["pass"])
        self.assertIn("UNFALSIFIABLE_DIAGNOSIS_NOT_CURRENTLY_ASSIGNED_TO_V4",out["errors"])
    def test_v4_blob_drift_fails_closed(self):
        recon,q,r,v=self.docs()
        out=evaluate(recon,q,r,"0"*40)
        self.assertFalse(out["pass"])
        self.assertIn("V4_SCORER_BLOB_DRIFT_FROM_COUNTEREXAMPLE_BASIS",out["errors"])
    def test_missing_independent_counterexample_evidence_fails_closed(self):
        recon,q,r,v=self.docs()
        r=copy.deepcopy(r)
        r["verified"]=[]
        out=evaluate(recon,q,r,v)
        self.assertFalse(out["pass"])

if __name__=="__main__": unittest.main(verbosity=2)
