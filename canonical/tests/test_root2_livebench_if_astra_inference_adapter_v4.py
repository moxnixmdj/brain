import unittest
from unittest import mock

from canonical.runtime import root2_livebench_if_astra_inference_adapter_v4 as v4


REQ = lambda text: {
    "benchmark_id": "LIVEBENCH_IF_2026_06_25",
    "task_id": "synthetic",
    "task_payload": {"instruction": text},
    "allowed_tools": [],
}


class LiveBenchAdapterV4Tests(unittest.TestCase):
    def test_overlap_fast_path_precedes_v3(self):
        prompt = (
            "Use induction to prove this claim. Consider a simple graph. "
            "Maintain a trigram overlap of 72% (±2%) with the provided reference text."
        )
        with mock.patch.object(v4.fallback_v3, "infer") as fallback:
            out = v4.infer(REQ(prompt))
        self.assertEqual(out["status"], "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertEqual(out["response_route"], "LIVEBENCH_IF_CHAR_TRIGRAM_OVERLAP_SOLVER_V1")
        self.assertEqual(out["model_dependency_count"], 0)
        fallback.assert_not_called()

    def test_non_overlap_preserves_v3(self):
        expected = {"status": "V3_FALLBACK"}
        with mock.patch.object(v4.fallback_v3, "infer", return_value=expected) as fallback:
            out = v4.infer(REQ("Explain photosynthesis clearly."))
        self.assertEqual(out, expected)
        fallback.assert_called_once()

    def test_external_tools_remain_forbidden(self):
        req = REQ("Explain photosynthesis.")
        req["allowed_tools"] = ["browser"]
        with self.assertRaises(v4.Root2InferenceBlocked):
            v4.infer(req)


if __name__ == "__main__":
    unittest.main()
