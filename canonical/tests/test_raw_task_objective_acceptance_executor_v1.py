from __future__ import annotations

import unittest

from canonical.runtime import raw_task_objective_acceptance_executor_v1 as a


class RawTaskObjectiveAcceptanceExecutorV1Tests(unittest.TestCase):
    def test_exact_response_accepts_and_authorizes_stop(self):
        out = a.evaluate_candidate(
            'Respond with exactly "YES".',
            {"response_text": "YES"},
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["candidate_accepted"], out)
        self.assertTrue(out["acceptance_stop_authorized"], out)
        self.assertEqual(out["semantic_residual_obligation_ids"], [])

    def test_wrong_exact_response_falsifies(self):
        out = a.evaluate_candidate(
            'Respond with exactly "YES".',
            {"response_text": "NO"},
        )
        self.assertFalse(out["pass"], out)
        self.assertFalse(out["candidate_accepted"], out)
        self.assertFalse(out["acceptance_stop_authorized"], out)
        self.assertEqual(out["status"], "FALSIFIED__OBJECTIVE_ACCEPTANCE_MODEL")

    def test_numeric_field_constraint_accepts(self):
        schema = {"score": {"type": "number", "dimension": "points"}}
        out = a.evaluate_candidate(
            "score must be at least 5.",
            {"fields": {"score": 6}},
            candidate_field_schema=schema,
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["acceptance_stop_authorized"], out)

    def test_numeric_field_constraint_rejects(self):
        schema = {"score": {"type": "number", "dimension": "points"}}
        out = a.evaluate_candidate(
            "score must be at least 5.",
            {"fields": {"score": 4}},
            candidate_field_schema=schema,
        )
        self.assertFalse(out["pass"], out)
        self.assertFalse(out["acceptance_stop_authorized"], out)

    def test_boolean_negative_control(self):
        schema = {"tests_pass": {"type": "boolean", "dimension": "dimensionless"}}
        passed = a.evaluate_candidate(
            "tests_pass must be true.",
            {"fields": {"tests_pass": True}},
            candidate_field_schema=schema,
        )
        failed = a.evaluate_candidate(
            "tests_pass must be true.",
            {"fields": {"tests_pass": False}},
            candidate_field_schema=schema,
        )
        self.assertTrue(passed["pass"], passed)
        self.assertFalse(failed["pass"], failed)

    def test_mixed_objective_and_semantic_task_blocks_stop(self):
        out = a.evaluate_candidate(
            'Respond with exactly "YES".\nCreate a polished financial report.',
            {"response_text": "YES"},
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "OPEN__SEMANTIC_ACCEPTANCE_RESIDUALS")
        self.assertFalse(out["acceptance_stop_authorized"], out)
        self.assertEqual(len(out["semantic_residual_obligation_ids"]), 1)

    def test_existing_tests_pass_evidence_cannot_replace_request_semantics(self):
        out = a.evaluate_candidate(
            "Fix the parser bug.",
            {"evidence": {"existing_tests_pass": True}},
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "OPEN__SEMANTIC_ACCEPTANCE_RESIDUALS")
        self.assertFalse(out["existing_test_success_is_complete_acceptance"])
        self.assertFalse(out["acceptance_stop_authorized"])

    def test_missing_required_candidate_field_fails_closed(self):
        schema = {"score": {"type": "number", "dimension": "points"}}
        out = a.evaluate_candidate(
            "score must be at least 5.",
            {"fields": {}},
            candidate_field_schema=schema,
        )
        self.assertFalse(out["pass"], out)
        self.assertFalse(out["acceptance_stop_authorized"], out)
        rr = out["obligation_results"][0]["route_results"]
        typed = next(x for x in rr if x["route_id"] == "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1")
        self.assertEqual(typed["status"], "FAIL_CLOSED")

    def test_unknown_candidate_field_fails_closed(self):
        out = a.evaluate_candidate(
            'Respond with exactly "YES".',
            {"response_text": "YES", "invented": True},
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertFalse(out["acceptance_stop_authorized"], out)

    def test_deterministic_same_inputs_same_receipts(self):
        kwargs = dict(
            task_text="score must be at least 5.",
            candidate={"fields": {"score": 6}},
            candidate_field_schema={
                "score": {"type": "number", "dimension": "points"}
            },
        )
        x = a.evaluate_candidate(**kwargs)
        y = a.evaluate_candidate(**kwargs)
        self.assertEqual(x["candidate_sha256"], y["candidate_sha256"])
        self.assertEqual(x["model_sha256"], y["model_sha256"])
        self.assertEqual(x["obligation_results"], y["obligation_results"])

    def test_two_fully_objective_segments_compose(self):
        schema = {"score": {"type": "number", "dimension": "points"}}
        out = a.evaluate_candidate(
            'Respond with exactly "YES".\nscore must be at least 5.',
            {"response_text": "YES", "fields": {"score": 6}},
            candidate_field_schema=schema,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["required_obligation_count"], 2)
        self.assertEqual(out["evaluated_obligation_count"], 2)
        self.assertTrue(all(x["pass"] for x in out["obligation_results"]))

    def test_compile_model_preserves_every_raw_obligation(self):
        out = a.compile_model(
            'Respond with exactly "YES".\nCreate a polished report.',
        )
        self.assertTrue(out["pass"], out)
        loc = out["localization"]
        self.assertEqual(
            loc["required_obligation_count"],
            loc["accounted_obligation_count"],
        )
        self.assertTrue(loc["all_required_obligations_accounted_for"])
        self.assertFalse(out["objective_acceptance_model_complete"])

    def test_zero_external_runtime_cognition(self):
        self.assertEqual(a.MODEL_DEPENDENCY_COUNT, 0)
        self.assertEqual(a.EXTERNAL_MODEL_RUNTIME_CALLS, 0)
        out = a.evaluate_candidate(
            'Respond with exactly "YES".',
            {"response_text": "YES"},
        )
        self.assertEqual(out["model_dependency_count"], 0)
        self.assertEqual(
            out["external_general_purpose_model_runtime_dependency_count"], 0
        )
        self.assertFalse(out["benchmark_identifier_used_for_routing"])
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
