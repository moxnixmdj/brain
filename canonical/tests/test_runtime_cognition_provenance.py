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

    def test_invalid_negative_dependency_count_fails_closed(self):
        with self.assertRaises(astra_runtime.Blocker):
            astra_runtime._stamp_cognition_provenance({
                "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
                "model_dependency_count":-1,
            })

    def test_missing_controller_mode_fails_closed(self):
        with self.assertRaises(astra_runtime.Blocker):
            astra_runtime._stamp_cognition_provenance({"final_summary":"ambiguous"})

    def test_unknown_controller_mode_fails_closed(self):
        with self.assertRaises(astra_runtime.Blocker):
            astra_runtime._stamp_cognition_provenance({
                "controller_mode":"UNCLASSIFIED_CONTROLLER",
                "final_summary":"ambiguous",
            })

    def test_model_independent_mode_with_planner_marker_is_contaminated(self):
        result=astra_runtime._stamp_cognition_provenance({
            "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
            "planner_source":"unexpected-planner",
            "planner_transport":None,
            "planner_model_last":None,
        })
        self.assertGreaterEqual(result["model_dependency_count"],1)
        self.assertEqual(result["cognition_dependency_class"],"MODEL_ASSISTED")

    def test_provenance_depth_overflow_fails_closed(self):
        nested={}
        cursor=nested
        for _ in range(26):
            cursor["child"]={}
            cursor=cursor["child"]
        with self.assertRaises(astra_runtime.Blocker):
            astra_runtime._stamp_cognition_provenance({
                "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
                "trace":nested,
            })


if __name__=="__main__":
    unittest.main()
