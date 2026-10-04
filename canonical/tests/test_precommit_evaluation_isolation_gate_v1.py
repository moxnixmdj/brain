from __future__ import annotations

import copy
import unittest

from canonical.runtime.precommit_evaluation_isolation_gate_v1 import (
    INPUT_SCHEMA,
    evaluate_isolation,
)

SHA_A = "a" * 40
H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64
H5 = "5" * 64
H6 = "6" * 64


def receipt(path: str):
    return {"path": path, "git_blob_sha": SHA_A}


def block(path: str):
    return {"verified": True, "independent": True, "receipt": receipt(path)}


def base():
    capsule = {
        "candidate_sha256": H1,
        "harness_sha256": H2,
        "scorer_sha256": H3,
        "environment_sha256": H4,
        "policy_sha256": H5,
        "benchmark_contract_sha256": H6,
        "frozen": True,
    }
    commitment = {
        **block("canonical/verification/commitment.json"),
        "bound_digests": {k: v for k, v in capsule.items() if k.endswith("_sha256")},
        "committed_before_terminal_case_access": True,
        "commitment_append_only": True,
    }
    runner = {
        **block("canonical/verification/runner.json"),
        "read_only_inputs": True,
        "candidate_write_disabled": True,
        "harness_write_disabled": True,
        "scorer_write_disabled": True,
        "outputs_separate_from_candidate_state": True,
        "executor_identity_independent": True,
    }
    leakage = {
        **block("canonical/verification/leakage.json"),
        "terminal_cases_exposed_before_commitment": False,
        "score_feedback_to_candidate": False,
        "adaptive_retry_on_terminal_case_content": False,
        "mutable_external_memory_shared_with_candidate": False,
        "candidate_network_egress_policy": "PINNED_ALLOWLIST",
    }
    invalidation = {
        **block("canonical/verification/invalidation.json"),
        "any_digest_change_invalidates": True,
        "post_commit_candidate_change_invalidates": True,
        "retry_requires_new_commitment": True,
        "case_access_before_commitment_invalidates": True,
    }
    return {
        "schema": INPUT_SCHEMA,
        "capsule": capsule,
        "commitment": commitment,
        "runner": runner,
        "leakage_controls": leakage,
        "invalidation": invalidation,
    }


class PrecommitEvaluationIsolationGateTests(unittest.TestCase):
    def test_complete_isolation_preconditions_pass_without_authority(self):
        out = evaluate_isolation(base())
        self.assertTrue(out["isolation_preconditions_proved"], out)
        self.assertTrue(out["parallel_execution_eligible_candidate"])
        self.assertFalse(out["fresh_reality_authority"])
        self.assertFalse(out["global_fresh_reality_gate_overridden"])
        self.assertFalse(out["benchmark_equivalence_proved"])
        self.assertEqual(out["acceptance_credit_delta"], 0)

    def test_case_exposure_before_commitment_stays_open(self):
        d = base()
        d["leakage_controls"]["terminal_cases_exposed_before_commitment"] = True
        out = evaluate_isolation(d)
        self.assertFalse(out["isolation_preconditions_proved"])
        self.assertIn(
            "LEAKAGE_CONTROLS_TERMINAL_CASES_EXPOSED_BEFORE_COMMITMENT_MUST_BE_FALSE",
            out["residual"],
        )

    def test_candidate_mutability_stays_open(self):
        d = base()
        d["runner"]["candidate_write_disabled"] = False
        out = evaluate_isolation(d)
        self.assertFalse(out["isolation_preconditions_proved"])
        self.assertIn("RUNNER_CANDIDATE_WRITE_DISABLED_REQUIRED", out["residual"])

    def test_digest_change_without_recommit_stays_open(self):
        d = base()
        d["capsule"]["candidate_sha256"] = "7" * 64
        out = evaluate_isolation(d)
        self.assertFalse(out["isolation_preconditions_proved"])
        self.assertIn("COMMITMENT_DIGEST_MISMATCH:candidate_sha256", out["residual"])

    def test_unverified_control_receipt_fails_closed(self):
        d = base()
        d["runner"]["independent"] = False
        out = evaluate_isolation(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("RUNNER_INDEPENDENT_REQUIRED", out["errors"])

    def test_bad_digest_fails_closed(self):
        d = base()
        d["capsule"]["policy_sha256"] = "not-a-sha"
        out = evaluate_isolation(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CAPSULE_POLICY_SHA256_INVALID", out["errors"])

    def test_unpinned_network_policy_stays_open(self):
        d = base()
        d["leakage_controls"]["candidate_network_egress_policy"] = "OPEN_INTERNET"
        out = evaluate_isolation(d)
        self.assertFalse(out["isolation_preconditions_proved"])
        self.assertIn(
            "LEAKAGE_CONTROLS_CANDIDATE_NETWORK_EGRESS_POLICY_INVALID",
            out["residual"],
        )

    def test_missing_invalidation_control_stays_open(self):
        d = base()
        d["invalidation"]["retry_requires_new_commitment"] = False
        out = evaluate_isolation(d)
        self.assertFalse(out["isolation_preconditions_proved"])
        self.assertIn("INVALIDATION_RETRY_REQUIRES_NEW_COMMITMENT_REQUIRED", out["residual"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
