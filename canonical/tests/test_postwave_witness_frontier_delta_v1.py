from __future__ import annotations
import copy, json, unittest
from pathlib import Path

from canonical.runtime.postwave_witness_frontier_delta_v1 import compile_frontier

ROOT=Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class PostwaveWitnessFrontierDeltaTests(unittest.TestCase):
    def docs(self):
        return (
            load("canonical/reasoning/2026-10-02_POSTWAVE_STRONGER_PROOF_RESATURATION_V1.json"),
            load("canonical/governance/P1_TERMINAL_EXECUTION_SCOPE_MISMATCH_QUARANTINE_V1.json"),
            load("canonical/verification/OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
            load("canonical/verification/OPUS55_SYNTHESIS_IMPLICATION_RESIDUAL_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json"),
        )

    def test_live_frontier_admits_only_p3_and_quarantines_p1(self):
        out=compile_frontier(*self.docs())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["admitted_candidate_count"],1)
        self.assertEqual(out["admitted_candidates"][0]["id"],"P3_GROUNDED_SYNTHESIS_POSTWAVE_WITNESS")
        self.assertEqual(out["admitted_candidates"][0]["proved_atom_count"],7)
        self.assertTrue(out["admitted_candidates"][0]["missing_scope_relation"])
        self.assertEqual(out["admitted_candidates"][0]["missing_atoms"],["metric:matched_quality"])
        self.assertEqual(
            set(out["admitted_candidates"][0]["missing_metric_bounds"]),
            {"matched_quality_noninferiority","required_claim_coverage_noninferiority"},
        )
        self.assertEqual(out["excluded_candidates"][0]["id"],"P1_TRAJECTORY_CAUSAL_RECOVERY_POSTWAVE_WITNESS")
        self.assertEqual(out["excluded_candidates"][0]["reason"],"INDEPENDENT_P1_SCOPE_QUARANTINE_ACTIVE")
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_p1_quarantine_must_be_independently_active(self):
        resat,p1q,p3bind,p3resid=self.docs()
        p1q=copy.deepcopy(p1q)
        p1q["independent_scope_mismatch_proved"]=False
        out=compile_frontier(resat,p1q,p3bind,p3resid)
        self.assertFalse(out["pass"])
        self.assertIn("P1_SCOPE_QUARANTINE_NOT_INDEPENDENTLY_PROVED",out["errors"])

    def test_p3_numeric_overclaim_is_rejected(self):
        resat,p1q,p3bind,p3resid=self.docs()
        p3bind=copy.deepcopy(p3bind)
        p3bind["numeric_metric_bounds_verified"]=True
        out=compile_frontier(resat,p1q,p3bind,p3resid)
        self.assertFalse(out["pass"])
        self.assertIn("P3_BINDING_NUMERIC_SCOPE_DRIFT",out["errors"])

    def test_p3_scope_overclaim_is_rejected(self):
        resat,p1q,p3bind,p3resid=self.docs()
        p3resid=copy.deepcopy(p3resid)
        p3resid["result"]["missing_scope_relation"]=False
        out=compile_frontier(resat,p1q,p3bind,p3resid)
        self.assertFalse(out["pass"])
        self.assertIn("P3_SCOPE_HOLE_NOT_PRESERVED",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
