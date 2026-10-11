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
            "target_reference_match": {
                "reference_system": "Claude Opus 5.5",
                "reference_score_percent": "40.0",
                "reference_origin": "ZAPIER_RUN_REPORTED_BY_ANTHROPIC",
                "exact_epoch_or_owner_bridge": True,
                "population_scope_comparable": True,
                "scoring_semantics_comparable": True,
                "tool_protocol_comparable": True,
                "step_limit_comparable": True,
                "fallback_policy_comparable": True,
                "binding_sha256": "4" * 64,
            },
        },
        "success_count": 263,
        "aggregate_score_percent": "40.03",
    }


class Tests(unittest.TestCase):
    def test_263_of_owner_attested_657_locks_pass(self):
        out = evaluate(valid_receipt())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["threshold_success_count"], 263)
        self.assertEqual(out["decision"], "PASS_LOCKED")

    def test_262_of_owner_attested_657_locks_fail(self):
        receipt = valid_receipt()
        receipt["success_count"] = 262
        receipt["aggregate_score_percent"] = "39.88"
        out = evaluate(receipt)
        self.assertEqual(out["decision"], "FAIL_LOCKED")

    def test_public_population_is_rejected(self):
        receipt = valid_receipt()
        receipt["population"]["kind"] = "PUBLIC"
        out = evaluate(receipt)
        self.assertFalse(out["pass"])
        self.assertIn("PRIVATE_HELD_OUT_SCOPE_REQUIRED", out["errors"])

    def test_exact_reference_epoch_or_owner_bridge_is_required(self):
        receipt = valid_receipt()
        receipt["owner_attestation"]["target_reference_match"][
            "exact_epoch_or_owner_bridge"
        ] = False
        out = evaluate(receipt)
        self.assertFalse(out["pass"])
        self.assertIn("EXACT_REFERENCE_EPOCH_OR_OWNER_BRIDGE_REQUIRED", out["errors"])

    def test_population_scope_match_is_required(self):
        receipt = valid_receipt()
        receipt["owner_attestation"]["target_reference_match"][
            "population_scope_comparable"
        ] = False
        out = evaluate(receipt)
        self.assertIn("REFERENCE_POPULATION_SCOPE_MATCH_REQUIRED", out["errors"])

    def test_protocol_match_is_required(self):
        receipt = valid_receipt()
        receipt["owner_attestation"]["target_reference_match"][
            "tool_protocol_comparable"
        ] = False
        out = evaluate(receipt)
        self.assertIn("REFERENCE_TOOL_PROTOCOL_MATCH_REQUIRED", out["errors"])

    def test_no_fallback_models_required(self):
        receipt = valid_receipt()
        receipt["fallback_models_used"] = True
        out = evaluate(receipt)
        self.assertIn("NO_FALLBACK_MODELS_REQUIRED", out["errors"])

    def test_current_public_version_is_not_assumed_to_be_target_epoch(self):
        receipt = valid_receipt()
        receipt["benchmark_version"] = "owner-private-epoch-X"
        out = evaluate(receipt)
        self.assertEqual(out["decision"], "PASS_LOCKED")

    def test_denominator_is_not_hardcoded_to_657(self):
        receipt = valid_receipt()
        receipt["population"]["denominator"] = 1000
        receipt["success_count"] = 400
        receipt["aggregate_score_percent"] = "40.0"
        out = evaluate(receipt)
        self.assertEqual(out["threshold_success_count"], 400)
        self.assertEqual(out["decision"], "PASS_LOCKED")

    def test_bad_owner_receipt_digest_fails_closed(self):
        receipt = valid_receipt()
        receipt["owner_attestation"]["receipt_sha256"] = "bad"
        out = evaluate(receipt)
        self.assertIn("OWNER_RECEIPT_SHA256_REQUIRED", out["errors"])

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

    def test_success_count_cannot_exceed_denominator(self):
        receipt = valid_receipt()
        receipt["success_count"] = 658
        receipt["aggregate_score_percent"] = "100"
        out = evaluate(receipt)
        self.assertIn("SUCCESS_COUNT_EXCEEDS_DENOMINATOR", out["errors"])

    def test_verifier_never_self_promotes_project_credit(self):
        out = evaluate(valid_receipt())
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertEqual(out["acceptance_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
