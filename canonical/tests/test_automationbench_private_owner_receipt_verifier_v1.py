from __future__ import annotations

import unittest

from canonical.runtime.automationbench_private_owner_receipt_verifier_v1 import evaluate


def valid_receipt():
    return {
        "schema": "PROJECT_BRAIN_AUTOMATIONBENCH_PRIVATE_OWNER_RECEIPT_V1",
        "benchmark_name": "AutomationBench",
        "benchmark_version": "1.0.6",
        "population": {
            "kind": "PRIVATE_HELD_OUT",
            "official_leaderboard_population": True,
            "population_identity_sha256": "1" * 64,
            "denominator": 657,
        },
        "tool_mode": "api",
        "max_steps_per_task": 50,
        "task_success_metric": "task_completed_correctly",
        "fallback_models_used": False,
        "candidate": {
            "content_sha256": "2" * 64,
            "all_execution_components_bound": True,
        },
        "owner_attestation": {
            "issuer_kind": "ZAPIER",
            "official_v1_0_6_private_leaderboard_surface": True,
            "receipt_path": "owner://zapier/automationbench/run-1",
            "receipt_sha256": "3" * 64,
            "independent_verified": True,
            "run_epoch": "2026-10-11T00:00:00Z",
        },
        "success_count": 263,
        "aggregate_score_percent": "40.03",
    }


class Tests(unittest.TestCase):
    def test_263_of_657_locks_pass(self):
        out = evaluate(valid_receipt())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["threshold_success_count"], 263)
        self.assertEqual(out["decision"], "PASS_LOCKED")

    def test_262_of_657_locks_fail(self):
        receipt = valid_receipt()
        receipt["success_count"] = 262
        receipt["aggregate_score_percent"] = "39.88"
        out = evaluate(receipt)
        self.assertEqual(out["decision"], "FAIL_LOCKED")

    def test_public_population_is_rejected(self):
        receipt = valid_receipt()
        receipt["population"]["kind"] = "PUBLIC"
        out = evaluate(receipt)
        self.assertIn("PRIVATE_HELD_OUT_SCOPE_REQUIRED", out["errors"])

    def test_official_population_attestation_is_required(self):
        receipt = valid_receipt()
        receipt["population"]["official_leaderboard_population"] = False
        out = evaluate(receipt)
        self.assertIn(
            "OFFICIAL_LEADERBOARD_POPULATION_ATTESTATION_REQUIRED", out["errors"]
        )

    def test_version_must_match_current_official_surface(self):
        receipt = valid_receipt()
        receipt["benchmark_version"] = "1.0.5"
        out = evaluate(receipt)
        self.assertIn("BENCHMARK_VERSION_MISMATCH", out["errors"])

    def test_denominator_must_match_current_private_population(self):
        receipt = valid_receipt()
        receipt["population"]["denominator"] = 600
        out = evaluate(receipt)
        self.assertIn("PRIVATE_POPULATION_DENOMINATOR_MISMATCH", out["errors"])

    def test_api_mode_is_required(self):
        receipt = valid_receipt()
        receipt["tool_mode"] = "zapier"
        out = evaluate(receipt)
        self.assertIn("TOOL_MODE_MISMATCH", out["errors"])

    def test_50_step_limit_is_required(self):
        receipt = valid_receipt()
        receipt["max_steps_per_task"] = 49
        out = evaluate(receipt)
        self.assertIn("MAX_STEPS_MISMATCH", out["errors"])

    def test_fallback_use_is_allowed_when_bound_into_candidate(self):
        receipt = valid_receipt()
        receipt["fallback_models_used"] = True
        out = evaluate(receipt)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["fallback_models_used"])

    def test_fallback_policy_must_be_explicit(self):
        receipt = valid_receipt()
        receipt.pop("fallback_models_used")
        out = evaluate(receipt)
        self.assertIn("FALLBACK_POLICY_MUST_BE_EXPLICIT_BOOLEAN", out["errors"])

    def test_all_execution_components_must_be_bound(self):
        receipt = valid_receipt()
        receipt["candidate"]["all_execution_components_bound"] = False
        out = evaluate(receipt)
        self.assertIn("ALL_EXECUTION_COMPONENTS_MUST_BE_BOUND", out["errors"])

    def test_owner_must_attest_official_v1_0_6_private_surface(self):
        receipt = valid_receipt()
        receipt["owner_attestation"][
            "official_v1_0_6_private_leaderboard_surface"
        ] = False
        out = evaluate(receipt)
        self.assertIn(
            "OFFICIAL_V1_0_6_PRIVATE_SURFACE_ATTESTATION_REQUIRED", out["errors"]
        )

    def test_owner_independent_verification_required(self):
        receipt = valid_receipt()
        receipt["owner_attestation"]["independent_verified"] = False
        out = evaluate(receipt)
        self.assertIn("INDEPENDENT_OWNER_VERIFICATION_REQUIRED", out["errors"])

    def test_inconsistent_reported_score_fails_closed(self):
        receipt = valid_receipt()
        receipt["aggregate_score_percent"] = "45.0"
        out = evaluate(receipt)
        self.assertIn(
            "REPORTED_SCORE_INCONSISTENT_WITH_SUCCESS_COUNT_AND_DENOMINATOR",
            out["errors"],
        )

    def test_verifier_never_self_promotes_project_credit(self):
        out = evaluate(valid_receipt())
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertEqual(out["acceptance_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
