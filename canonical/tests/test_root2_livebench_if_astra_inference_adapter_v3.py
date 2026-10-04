import unittest
from unittest import mock

from canonical.runtime import root2_livebench_if_astra_inference_adapter_v3 as v3


REQ = lambda text: {
    "benchmark_id": "LIVEBENCH_IF_2026_06_25",
    "task_id": "synthetic",
    "task_payload": {"instruction": text},
    "allowed_tools": [],
}


def BASE(answer: str) -> dict:
    return {
        "task_id": "synthetic",
        "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
        "answer": answer,
        "artifacts": [],
        "tool_trace": [],
        "cognition_dependency_class": "MODEL_INDEPENDENT",
        "model_dependency_count": 0,
    }


class LiveBenchAdapterV3Tests(unittest.TestCase):
    def test_v2_exact_fast_path_is_preserved(self):
        out = v3.infer(REQ('Reply with exactly "ALPHA".'))
        self.assertEqual(out["status"], "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertEqual(out["answer"], "ALPHA")
        self.assertEqual(
            out["response_route"],
            "VERIFIED_GENERIC_FORMAL_CONSTRAINT_COMPILER_V1",
        )

    def test_plain_semantic_request_is_unchanged(self):
        expected = BASE("Plants convert light into stored chemical energy.")
        with mock.patch.object(v3.v2.fallback_v1, "infer", return_value=expected) as f:
            out = v3.infer(REQ("Explain photosynthesis clearly."))
        self.assertEqual(out, expected)
        f.assert_called_once()

    def test_lowercase_constraint_is_composed_over_semantic_seed(self):
        expected = BASE("Plants Convert Light Into Chemical Energy.")
        with mock.patch.object(v3.v2.fallback_v1, "infer", return_value=expected):
            out = v3.infer(
                REQ("Explain photosynthesis. Write the entire response in lowercase only.")
            )
        self.assertEqual(out["answer"], "plants convert light into chemical energy.")
        self.assertEqual(
            out["response_route"],
            "V1_SEMANTIC_SEED__VERIFIED_SEED_PRESERVING_POSTPROCESSOR_V1",
        )
        self.assertTrue(out["formal_postvalidation"])
        self.assertIn("LOWERCASE", out["postprocessor_applied_transforms"])

    def test_prefix_and_suffix_are_composed_over_semantic_seed(self):
        expected = BASE("core answer")
        with mock.patch.object(v3.v2.fallback_v1, "infer", return_value=expected):
            out = v3.infer(
                REQ(
                    'Explain the result. Response must start with "BEGIN" '
                    'and response must end with "END"'
                )
            )
        self.assertTrue(out["answer"].startswith("BEGIN"))
        self.assertTrue(out["answer"].endswith("END"))
        self.assertTrue(out["formal_postvalidation"])

    def test_already_satisfied_word_floor_is_certified_without_mutation(self):
        expected = BASE("one two three four five")
        with mock.patch.object(v3.v2.fallback_v1, "infer", return_value=expected):
            out = v3.infer(REQ("Explain briefly using at least 5 words."))
        self.assertEqual(out["answer"], expected["answer"])
        self.assertTrue(out["formal_postvalidation"])

    def test_unsafe_semantic_deletion_fails_closed(self):
        expected = BASE("the semantic answer contains banana")
        with mock.patch.object(v3.v2.fallback_v1, "infer", return_value=expected):
            with self.assertRaises(v3.Root2InferenceBlocked) as ctx:
                v3.infer(
                    REQ('Explain the result. Do not include the word "banana"')
                )
        self.assertIn("FORMAL_CONSTRAINT_POSTPROCESS_FAILED", str(ctx.exception))
        self.assertIn("FORBIDDEN_LITERAL:banana", str(ctx.exception))

    def test_nonzero_model_dependency_is_rejected(self):
        expected = BASE("seed")
        expected["model_dependency_count"] = 1
        with mock.patch.object(v3.v2.fallback_v1, "infer", return_value=expected):
            with self.assertRaises(v3.Root2InferenceBlocked):
                v3.infer(REQ("Answer using lowercase only."))

    def test_external_tools_remain_forbidden(self):
        req = REQ('Reply with exactly "ALPHA".')
        req["allowed_tools"] = ["browser"]
        with self.assertRaises(v3.Root2InferenceBlocked):
            v3.infer(req)


if __name__ == "__main__":
    unittest.main()
