from __future__ import annotations

import copy
import unittest

from canonical.runtime.automationbench_private_owner_receipt_verifier_v1 import evaluate


def valid_receipt():
    return {
        "schema": "PROJECT_BRAIN_AUTOMATIONBENCH_PRIVATE_OWNER_RECEIPT_V1",
        "benchmark_name": "AutomationBench",
        "benchmark_version": "1.0.6",
        "population": {
            "kind": "PRIVATE_HELD_OUT",
            "scope_match_to_target_reference": True,
            "population_identity_sha256": "1" * 64,
            "denominator": 657,
        },
        "tool_mode": "api",
        "max_steps_per_task": 50,
        "task_success_metric": "task_completed_correctly",
        "fallback_models_used": False,
        "candidate": {"content_sha256": "2" * 64},
        "owner_attestation": {
            "issuer_kind": "ZAPIER",
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
        self.assertTrue(out["predicate_satisfied"])

    def test_262_of_657_locks_fail(self):
        receipt = valid_receipt()
        receipt["success_count"] = 262
        receipt["aggregate_score_percent"] = "39.88"
        out = evaluate(receipt)
        self.assertEqual(out["threshold_success_count"], 263)
        self.assertEqual(out["decision"], "FAIL_LOCKED")
        self.assertFalse(out["predicate_satisfied"])

    def test_public_population_cannot_substitute(self):
        receipt = valid_receipt()
        receipt["population"]["kind"] = "PUBLIC"
        out = evaluate(receipt)
        self.assertFalse(out["pass"])
        self.assertIn("PRIVATE_HELD_OUT_SCOPE_REQUIRED", out["errors"])

    def test_scope_match_must_be_owner_attested(self):
        receipt = valid_receipt()
        receipt["population"]["scope_match_to_target_reference"] = False
        out = evaluate(receipt)
        self.assertFalse(out["pass"])
        self.assertIn("TARGET_REFERENCE_SCOPE_MATCH_NOT_ATTESTED", out["errors"])

    def test_fallback_models_fail_closed(self):
        receipt = valid_receipt()
        receipt["fallback_models_used"] = True
        out = evaluate(receipt)
        self.assertFalse(out["pass"])
        self.assertIn("NO_FALLBACK_MODELS_REQUIRED", out["errors"])

    def test_version_mismatch_fails_closed(self):
        receipt = valid_receipt()
        receipt["benchmark_version"] = "1.0.5"
        out = evaluate(receipt)
        self.assertFalse(out["pass"])
        self.assertIn("BENCHMARK_VERSION_MISMATCH", out["errors"])

    def test_tool_mode_mismatch_fails_closed(self):
        receipt = valid_receipt()
        receipt["tool_mode"] = "zapier"
        out = evaluate(receipt)
        self.assertFalse(out["pass"])
        self.assertIn("TOOL_MODE_MISMATCH", out["errors"])

    def test_step_cap_mismatch_fails_closed(self):
        receipt = valid_receipt()
        receipt["max_steps_per_task"] = 49
        out = evaluate(receipt)
        self.assertFalse(out["pass"])
        self.assertIn("MAX_STEPS_MISMATCH", out["errors"])

    def test_owner_verification_is_required(self):
        receipt = valid_receipt()
        receipt["owner_attestation"]["independent_verified"] = False
        out = evaluate(receipt)
        self.assertFalse(out["pass"])
        self.assertIn("INDEPENDENT_OWNER_VERIFICATION_REQUIRED", out["errors"])

    def test_bad_content_address_fails_closed(self):
        receipt = valid_receipt()
        receipt["owner_attestation"]["receipt_sha256"] = "not-a-sha"
        out = evaluate(receipt)
        self.assertFalse(out["pass"])
        self.assertIn("OWNER_RECEIPT_SHA256_REQUIRED", out["errors"])

    def test_inconsistent_reported_score_fails_closed(self):
        receipt = valid_receipt()
        receipt["aggregate_score_percent"] = "45.0"
        out = evaluate(receipt)
        self.assertFalse(out["pass"])
        self.assertIn(
            "REPORTED_SCORE_INCONSISTENT_WITH_SUCCESS_COUNT_AND_DENOMINATOR",
            out["errors"],
        )

    def test_exact_matched_population_need_not_be_hardcoded_to_657(self):
        receipt = valid_receipt()
        receipt["population"]["denominator"] = 1000
        receipt["success_count"] = 400
        receipt["aggregate_score_percent"] = "40.0"
        out = evaluate(receipt)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["threshold_success_count"], 400)
        self.assertEqual(out["decision"], "PASS_LOCKED")

    def test_success_count_cannot_exceed_denominator(self):
        receipt = valid_receipt()
        receipt["success_count"] = 658
        receipt["aggregate_score_percent"] = "100"
        out = evaluate(receipt)
        self.assertFalse(out["pass"])
        self.assertIn("SUCCESS_COUNT_EXCEEDS_DENOMINATOR", out["errors"])

    def test_verifier_never_grants_project_promotion_authority(self):
        out = evaluate(valid_receipt())
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertEqual(out["acceptance_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
