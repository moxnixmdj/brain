from __future__ import annotations
import unittest
from canonical.runtime import root2_external_task_entrypoint_v1 as ep

class TestRoot2ExternalTaskEntrypointV1(unittest.TestCase):
    def test_livebench_inference_adapter_preflight_passes(self):
        out=ep.preflight("LIVEBENCH_IF_2026_06_25")
        self.assertTrue(out["inference_ready"])
        self.assertEqual(out["status"],"PASS__INFERENCE_ADAPTER_BOUND")

    def test_unknown_benchmark_fails_closed(self):
        out=ep.preflight("NOT_A_REAL_BENCHMARK")
        self.assertFalse(out["inference_ready"])
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_invoke_rejects_malformed_livebench_request(self):
        with self.assertRaises(Exception):
            ep.invoke({"benchmark_id":"LIVEBENCH_IF_2026_06_25","task_id":"synthetic","task_payload":{}})

if __name__=="__main__":
    unittest.main()
