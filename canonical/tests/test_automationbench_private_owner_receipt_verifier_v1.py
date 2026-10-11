from __future__ import annotations

import unittest

from canonical.runtime.automationbench_private_owner_receipt_verifier_v1 import evaluate


def zapier_receipt():
    return {
        "schema": "PROJECT_BRAIN_AUTOMATIONBENCH_PRIVATE_OWNER_RECEIPT_V1",
        "benchmark_name": "AutomationBench",
        "benchmark_version": "1.0.6",
        "evaluation_surface": "ZAPIER_PRIVATE_LEADERBOARD",
        "population": {
            "kind": "PRIVATE_HELD_OUT",
            "zapier_private_v1_0_6_657": True,
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


def aa_receipt():
    r = zapier_receipt()
    r["evaluation_surface"] = "ARTIFICIAL_ANALYSIS_AUTOMATIONBENCH_AA"
    r["task_success_metric"] = "tasks_completed"
    r["owner_attestation"] = {
        "issuer_kind": "ARTIFICIAL_ANALYSIS",
        "automationbench_aa_private_657_v1_0_6_in_collaboration_with_zapier": True,
        "every_assertion_classified_objective_or_guardrail": True,
        "tasks_completed_requires_every_objective_and_no_guardrail_violation": True,
        "deterministic_final_state_grading": True,
        "receipt_path": "owner://artificial-analysis/automationbench-aa/run-1",
        "receipt_sha256": "4" * 64,
        "independent_verified": True,
        "run_epoch": "2026-10-11T00:00:00Z",
    }
    return r


class Tests(unittest.TestCase):
    def test_zapier_263_of_657_locks_pass(self):
        out = evaluate(zapier_receipt())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["threshold_success_count"], 263)
        self.assertEqual(out["decision"], "PASS_LOCKED")

    def test_aa_tasks_completed_263_of_657_locks_pass(self):
        out = evaluate(aa_receipt())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["decision"], "PASS_LOCKED")
        self.assertEqual(out["normalized_task_success_metric"], "task_completed_correctly")

    def test_262_of_657_locks_fail_on_both_surfaces(self):
        for factory in (zapier_receipt, aa_receipt):
            receipt = factory()
            receipt["success_count"] = 262
            receipt["aggregate_score_percent"] = "39.88"
            out = evaluate(receipt)
            self.assertEqual(out["decision"], "FAIL_LOCKED")

    def test_public_population_is_rejected(self):
        receipt = zapier_receipt()
        receipt["population"]["kind"] = "PUBLIC"
        out = evaluate(receipt)
        self.assertIn("PRIVATE_HELD_OUT_SCOPE_REQUIRED", out["errors"])

    def test_exact_private_population_binding_is_required(self):
        receipt = aa_receipt()
        receipt["population"]["zapier_private_v1_0_6_657"] = False
        out = evaluate(receipt)
        self.assertIn("ZAPIER_PRIVATE_V1_0_6_657_BINDING_REQUIRED", out["errors"])

    def test_version_must_match(self):
        receipt = zapier_receipt()
        receipt["benchmark_version"] = "1.0.5"
        out = evaluate(receipt)
        self.assertIn("BENCHMARK_VERSION_MISMATCH", out["errors"])

    def test_denominator_must_be_657(self):
        receipt = zapier_receipt()
        receipt["population"]["denominator"] = 600
        out = evaluate(receipt)
        self.assertIn("PRIVATE_POPULATION_DENOMINATOR_MISMATCH", out["errors"])

    def test_api_mode_is_required(self):
        receipt = zapier_receipt()
        receipt["tool_mode"] = "zapier"
        out = evaluate(receipt)
        self.assertIn("TOOL_MODE_MISMATCH", out["errors"])

    def test_50_turn_limit_is_required(self):
        receipt = zapier_receipt()
        receipt["max_steps_per_task"] = 49
        out = evaluate(receipt)
        self.assertIn("MAX_STEPS_MISMATCH", out["errors"])

    def test_aa_metric_must_be_tasks_completed(self):
        receipt = aa_receipt()
        receipt["task_success_metric"] = "score"
        out = evaluate(receipt)
        self.assertIn("AA_TASKS_COMPLETED_METRIC_REQUIRED", out["errors"])

    def test_aa_assertion_partition_is_required(self):
        receipt = aa_receipt()
        receipt["owner_attestation"]["every_assertion_classified_objective_or_guardrail"] = False
        out = evaluate(receipt)
        self.assertIn("AA_ASSERTION_PARTITION_BINDING_REQUIRED", out["errors"])

    def test_aa_strict_completion_semantics_are_required(self):
        receipt = aa_receipt()
        receipt["owner_attestation"]["tasks_completed_requires_every_objective_and_no_guardrail_violation"] = False
        out = evaluate(receipt)
        self.assertIn("AA_STRICT_COMPLETION_SEMANTICS_REQUIRED", out["errors"])

    def test_aa_requires_artificial_analysis_issuer(self):
        receipt = aa_receipt()
        receipt["owner_attestation"]["issuer_kind"] = "ZAPIER"
        out = evaluate(receipt)
        self.assertIn("AA_SURFACE_ISSUER_MISMATCH", out["errors"])

    def test_fallback_use_is_allowed_when_bound(self):
        receipt = aa_receipt()
        receipt["fallback_models_used"] = True
        out = evaluate(receipt)
        self.assertTrue(out["pass"], out)

    def test_all_execution_components_must_be_bound(self):
        receipt = zapier_receipt()
        receipt["candidate"]["all_execution_components_bound"] = False
        out = evaluate(receipt)
        self.assertIn("ALL_EXECUTION_COMPONENTS_MUST_BE_BOUND", out["errors"])

    def test_inconsistent_reported_score_fails_closed(self):
        receipt = aa_receipt()
        receipt["aggregate_score_percent"] = "45.0"
        out = evaluate(receipt)
        self.assertIn(
            "REPORTED_SCORE_INCONSISTENT_WITH_SUCCESS_COUNT_AND_DENOMINATOR",
            out["errors"],
        )

    def test_verifier_never_self_promotes_project_credit(self):
        for factory in (zapier_receipt, aa_receipt):
            out = evaluate(factory())
            self.assertFalse(out["promotion_authority"])
            self.assertFalse(out["execution_authority"])
            self.assertEqual(out["acceptance_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
