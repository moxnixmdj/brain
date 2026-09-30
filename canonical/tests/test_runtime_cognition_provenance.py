import unittest

from canonical.runtime import astra_runtime


class CognitionProvenanceTests(unittest.TestCase):
    def test_model_independent_goal_is_stamped_zero(self):
        result=astra_runtime._stamp_cognition_provenance({
            "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
            "planner_model_last":None,
            "final_summary":"ok",
        })
        self.assertEqual(result["model_dependency_count"],0)
        self.assertEqual(result["cognition_dependency_class"],"MODEL_INDEPENDENT")
        self.assertEqual(result["cognition_provenance_authority"],"ASTRA_RUNTIME_DERIVED_V1")

    def test_optional_model_advisory_is_contaminated(self):
        result=astra_runtime._stamp_cognition_provenance({
            "controller_mode":"OPTIONAL_MODEL_ADVISORY",
            "planner_model_last":"mistral",
            "final_summary":"ok",
        })
        self.assertGreaterEqual(result["model_dependency_count"],1)
        self.assertEqual(result["cognition_dependency_class"],"MODEL_ASSISTED")

    def test_nested_model_dependency_propagates(self):
        result=astra_runtime._stamp_cognition_provenance({
            "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
            "trace":[{"result":{"model_dependency_count":2}}],
        })
        self.assertEqual(result["model_dependency_count"],2)
        self.assertEqual(result["cognition_dependency_class"],"MODEL_ASSISTED")

    def test_missing_controller_mode_fails_closed(self):
        with self.assertRaisesRegex(astra_runtime.Blocker,"COGNITION_PROVENANCE_CONTROLLER_MODE_MISSING"):
            astra_runtime._stamp_cognition_provenance({"final_summary":"ok"})

    def test_unknown_controller_mode_fails_closed(self):
        with self.assertRaisesRegex(astra_runtime.Blocker,"COGNITION_PROVENANCE_CONTROLLER_MODE_UNKNOWN"):
            astra_runtime._stamp_cognition_provenance({
                "controller_mode":"UNTRUSTED_UNKNOWN_MODE",
                "final_summary":"ok",
            })

    def test_planner_source_marks_model_dependency(self):
        result=astra_runtime._stamp_cognition_provenance({
            "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
            "planner_source":"external-planner",
            "final_summary":"ok",
        })
        self.assertGreaterEqual(result["model_dependency_count"],1)
        self.assertEqual(result["cognition_dependency_class"],"MODEL_ASSISTED")

    def test_invalid_negative_dependency_count_fails_closed(self):
        with self.assertRaisesRegex(astra_runtime.Blocker,"MODEL_DEPENDENCY_COUNT_INVALID"):
            astra_runtime._stamp_cognition_provenance({
                "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
                "model_dependency_count":-1,
            })


    def test_direct_run_goal_entrypoint_is_runtime_stamped(self):
        original=astra_runtime._run_goal_unstamped
        try:
            astra_runtime._run_goal_unstamped=lambda step,mission: {
                "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
                "planner_model_last":None,
                "final_summary":"direct",
            }
            result=astra_runtime.run_goal({}, {})
        finally:
            astra_runtime._run_goal_unstamped=original
        self.assertEqual(result["model_dependency_count"],0)
        self.assertEqual(result["cognition_dependency_class"],"MODEL_INDEPENDENT")
        self.assertEqual(result["cognition_provenance_authority"],"ASTRA_RUNTIME_DERIVED_V1")

    def test_direct_run_goal_advisory_path_cannot_stamp_zero(self):
        original=astra_runtime._run_goal_unstamped
        try:
            astra_runtime._run_goal_unstamped=lambda step,mission: {
                "controller_mode":"OPTIONAL_MODEL_ADVISORY",
                "planner_source":"test-model-source",
                "planner_model_last":"test-model",
                "final_summary":"direct",
            }
            result=astra_runtime.run_goal({}, {})
        finally:
            astra_runtime._run_goal_unstamped=original
        self.assertGreaterEqual(result["model_dependency_count"],1)
        self.assertEqual(result["cognition_dependency_class"],"MODEL_ASSISTED")


if __name__=="__main__":
    unittest.main()
