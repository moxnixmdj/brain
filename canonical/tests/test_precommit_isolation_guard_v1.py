import importlib.util
from pathlib import Path
import unittest

P = Path(__file__).resolve().parents[1] / "runtime" / "precommit_isolation_guard_v1.py"
S = importlib.util.spec_from_file_location("pig", P)
M = importlib.util.module_from_spec(S)
assert S.loader
S.loader.exec_module(M)


def base_receipt():
    r = {
        "candidate_sha256": "1" * 64,
        "harness_sha256": "2" * 64,
        "scorer_sha256": "3" * 64,
        "environment_sha256": "4" * 64,
        "policy_sha256": "5" * 64,
        "commitment_recorded_before_case_reveal": True,
        "independent_executor": True,
        "candidate_immutable_during_execution": True,
        "no_adaptive_state_channel": True,
        "outputs_bound_to_commitment": True,
        "benchmark_protocol_comparability_verified": True,
        "observed_candidate_sha256": "1" * 64,
    }
    r["commitment_sha256"] = M.commitment_digest(r)
    return r


class TestPrecommitIsolationGuard(unittest.TestCase):
    def test_complete_receipt_passes_mechanical_gate_only(self):
        out = M.verify_precommit_isolation_receipt(base_receipt())
        self.assertTrue(out["mechanical_isolation_gate_pass"])
        self.assertFalse(out["fresh_reality_authority"])
        self.assertTrue(out["requires_benchmark_specific_semantic_proof"])

    def test_case_reveal_order_failure_rejected(self):
        r = base_receipt()
        r["commitment_recorded_before_case_reveal"] = False
        out = M.verify_precommit_isolation_receipt(r)
        self.assertFalse(out["mechanical_isolation_gate_pass"])
        self.assertIn("COMMITMENT_NOT_PROVED_BEFORE_CASE_REVEAL", out["reasons"])

    def test_candidate_drift_rejected(self):
        r = base_receipt()
        r["observed_candidate_sha256"] = "9" * 64
        out = M.verify_precommit_isolation_receipt(r)
        self.assertFalse(out["mechanical_isolation_gate_pass"])
        self.assertIn("EXECUTED_CANDIDATE_DIFFERS_FROM_COMMITTED_CANDIDATE", out["reasons"])


if __name__ == "__main__":
    unittest.main()
