from __future__ import annotations
import unittest
from canonical.runtime import root2_external_task_entrypoint_v1 as ep

class TestRoot2ExternalTaskEntrypointV1(unittest.TestCase):
    def test_livebench_postprocess_adapter_is_not_inference(self):
        out=ep.preflight("LIVEBENCH_IF_2026_06_25")
        self.assertFalse(out["inference_ready"])
        self.assertIn("ADAPTER_NOT_INFERENCE_CAPABLE",out["errors"])
        self.assertIn("ADAPTER_MODE_NOT_INFERENCE",out["errors"])

    def test_unknown_benchmark_fails_closed(self):
        out=ep.preflight("NOT_A_REAL_BENCHMARK")
        self.assertFalse(out["inference_ready"])
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_invoke_rejects_unbound_inference(self):
        with self.assertRaises(ep.ExternalTaskBlocked):
            ep.invoke({"benchmark_id":"LIVEBENCH_IF_2026_06_25","task_id":"synthetic","task_payload":{"x":1}})

if __name__=="__main__":
    unittest.main()
