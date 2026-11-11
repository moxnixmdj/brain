import unittest
from unittest import mock

from canonical.runtime import root2_livebench_if_astra_inference_adapter_v5 as v5

REQ = lambda text: {
    "benchmark_id": "LIVEBENCH_IF_2026_06_25",
    "task_id": "synthetic-v5",
    "task_payload": {"instruction": text},
    "allowed_tools": [],
}


class LiveBenchAdapterV5Tests(unittest.TestCase):
    def test_legacy_keyword_route_is_model_independent(self):
        out = v5.infer(REQ("Include keywords ['apple', 'river'] in the response."))
        self.assertEqual(out["status"], "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertEqual(out["response_route"], "LIVEBENCH_LEGACY25_PUBLIC_GRAMMAR_WITNESS_V1")
        self.assertEqual(out["model_dependency_count"], 0)
        self.assertIn("apple", out["answer"].lower())
        self.assertIn("river", out["answer"].lower())

    def test_recognized_langdetect_family_cannot_escape_to_v4(self):
        with mock.patch.object(v5.fallback_v4, "infer") as fallback:
            with self.assertRaises(v5.Root2InferenceBlocked):
                v5.infer(REQ("Your ENTIRE response should be in Spanish language, no other language is allowed."))
        fallback.assert_not_called()

    def test_unrecognized_request_preserves_v4(self):
        expected = {"status": "FALLBACK_V4"}
        with mock.patch.object(v5.fallback_v4, "infer", return_value=expected) as fallback:
            out = v5.infer(REQ("Explain photosynthesis clearly."))
        self.assertEqual(out, expected)
        fallback.assert_called_once()

    def test_request_firewall_still_blocks_tools(self):
        req = REQ("Include keywords ['apple'] in the response.")
        req["allowed_tools"] = ["browser"]
        with self.assertRaises(v5.Root2InferenceBlocked):
            v5.infer(req)


if __name__ == "__main__":
    unittest.main()
