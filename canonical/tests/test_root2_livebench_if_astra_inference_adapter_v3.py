import unittest
from unittest import mock

from canonical.runtime import instruction_constraint_compiler_v1 as compiler
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v3 as v3

REQ = lambda text: {
    "benchmark_id": "LIVEBENCH_IF_2026_06_25",
    "task_id": "synthetic",
    "task_payload": {"instruction": text},
    "allowed_tools": [],
}


class LiveBenchAdapterV3Tests(unittest.TestCase):
    def test_structural_unique_word_witness_no_longer_requires_semantic_runtime(self):
        out = v3.infer(REQ("Use at least 5 unique words in the response."))
        self.assertEqual(out["status"], "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertEqual(out["response_route"], "LIVEBENCH_IF_SCORE_ONLY_STRUCTURAL_WITNESS_V3")
        self.assertEqual(out["model_dependency_count"], 0)
        c = compiler.compile_constraints("Use at least 5 unique words in the response.")
        self.assertTrue(compiler.validate_response(out["answer"], c)[0])

    def test_composed_structural_witness_satisfies_all_recovered_constraints(self):
        text = (
            "Use at least 5 unique words in the response. "
            "Include exactly 2 numbers in the response."
        )
        out = v3.infer(REQ(text))
        self.assertEqual(out["response_route"], "LIVEBENCH_IF_SCORE_ONLY_STRUCTURAL_WITNESS_V3")
        self.assertTrue(compiler.validate_response(out["answer"], compiler.compile_constraints(text))[0])

    def test_exact_formal_route_remains_v2(self):
        out = v3.infer(REQ('Reply with exactly "ALPHA".'))
        self.assertEqual(out["answer"], "ALPHA")
        self.assertEqual(out["response_route"], "VERIFIED_GENERIC_FORMAL_CONSTRAINT_COMPILER_V1")

    def test_unrecognized_semantic_request_preserves_v2(self):
        expected = {"status": "FALLBACK_V2"}
        with mock.patch.object(v3.fallback_v2, "infer", return_value=expected) as f:
            out = v3.infer(REQ("Explain photosynthesis clearly."))
        self.assertEqual(out, expected)
        f.assert_called_once()

    def test_contradiction_preserves_v2_fail_closed_route(self):
        expected = {"status": "FALLBACK_V2"}
        with mock.patch.object(v3.fallback_v2, "infer", return_value=expected) as f:
            out = v3.infer(REQ('Reply with exactly "ALPHA". Use lowercase only.'))
        self.assertEqual(out, expected)
        f.assert_called_once()

    def test_external_tools_remain_forbidden_by_v2_firewall(self):
        req = REQ("Use at least 5 unique words in the response.")
        req["allowed_tools"] = ["browser"]
        with self.assertRaises(v3.Root2InferenceBlocked):
            v3.infer(req)


if __name__ == "__main__":
    unittest.main()
