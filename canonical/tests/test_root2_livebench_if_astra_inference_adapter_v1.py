from __future__ import annotations
import unittest
from unittest import mock
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v1 as adapter

class TestRoot2LiveBenchIFAstraInferenceAdapterV1(unittest.TestCase):
    def test_model_independent_result_passes(self):
        fake={
            "stdout":"answer",
            "trace":[],
            "cognition_dependency_class":"MODEL_INDEPENDENT",
            "model_dependency_count":0,
        }
        with mock.patch.object(adapter.astra_runtime,"run_goal",return_value=fake):
            out=adapter.infer({
                "benchmark_id":"LIVEBENCH_IF_2026_06_25",
                "task_id":"synthetic",
                "task_payload":{"instruction":"Rewrite this sentence."},
                "allowed_tools":[],
            })
        self.assertEqual(out["answer"],"answer")
        self.assertEqual(out["model_dependency_count"],0)

    def test_model_assisted_result_fails(self):
        fake={
            "stdout":"answer",
            "trace":[],
            "cognition_dependency_class":"MODEL_ASSISTED",
            "model_dependency_count":1,
        }
        with mock.patch.object(adapter.astra_runtime,"run_goal",return_value=fake):
            with self.assertRaises(adapter.Root2InferenceBlocked):
                adapter.infer({
                    "benchmark_id":"LIVEBENCH_IF_2026_06_25",
                    "task_id":"synthetic",
                    "task_payload":{"instruction":"Rewrite this sentence."},
                    "allowed_tools":[],
                })

    def test_external_tools_forbidden(self):
        with self.assertRaises(adapter.Root2InferenceBlocked):
            adapter.infer({
                "benchmark_id":"LIVEBENCH_IF_2026_06_25",
                "task_id":"synthetic",
                "task_payload":{"instruction":"test"},
                "allowed_tools":["web_search"],
            })

if __name__=="__main__":
    unittest.main()
