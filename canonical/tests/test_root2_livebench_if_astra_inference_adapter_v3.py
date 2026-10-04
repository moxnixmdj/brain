import unittest
from unittest import mock

from canonical.runtime import root2_livebench_if_astra_inference_adapter_v3 as v3


def req(text):
    return {
        "benchmark_id": "LIVEBENCH_IF_2026_06_25",
        "task_id": "synthetic",
        "task_payload": {"instruction": text},
        "allowed_tools": [],
    }


def base(answer):
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
    def test_semantic_seed_lowercase_constraint_is_repaired(self):
        with mock.patch.object(v3.base_v2, "infer", return_value=base("Mixed Case Semantic Answer")):
            out = v3.infer(req("Explain photosynthesis clearly. Write the entire response in lowercase only."))
        self.assertEqual(out["answer"], "mixed case semantic answer")
        self.assertIn("LOWERCASE", out["seed_postprocessor"]["applied_transforms"])
        self.assertEqual(out["model_dependency_count"], 0)

    def test_semantic_seed_prefix_suffix_are_repaired(self):
        with mock.patch.object(v3.base_v2, "infer", return_value=base("core semantic answer")):
            out = v3.infer(req('Explain the result. Response must start with "BEGIN" and response must end with "END".'))
        self.assertTrue(out["answer"].startswith("BEGIN"))
        self.assertTrue(out["answer"].endswith("END"))
        self.assertEqual(
            out["response_route"],
            "V2_THEN_SEED_PRESERVING_INSTRUCTION_POSTPROCESSOR_V1",
        )

    def test_no_structural_constraint_preserves_semantic_seed(self):
        with mock.patch.object(v3.base_v2, "infer", return_value=base("A grounded semantic answer.")):
            out = v3.infer(req("Explain the mechanism clearly."))
        self.assertEqual(out["answer"], "A grounded semantic answer.")
        self.assertTrue(out["seed_postprocessor"]["seed_preserved"])

    def test_unsafe_semantic_invention_fails_closed(self):
        with mock.patch.object(v3.base_v2, "infer", return_value=base("one two")):
            with self.assertRaises(v3.Root2InferenceBlocked) as ctx:
                v3.infer(req("Explain the mechanism with at least 5 words."))
        self.assertIn("UNSAFE_TRANSFORMATION_REQUIRED", str(ctx.exception))
        self.assertIn("MIN_WORDS", str(ctx.exception))

    def test_bad_dependency_provenance_fails_closed(self):
        bad = base("answer")
        bad["cognition_dependency_class"] = "MODEL_ASSISTED"
        bad["model_dependency_count"] = 1
        with mock.patch.object(v3.base_v2, "infer", return_value=bad):
            with self.assertRaises(v3.Root2InferenceBlocked):
                v3.infer(req("Explain the mechanism clearly."))

    def test_external_tools_remain_forbidden(self):
        r = req('Reply with exactly "ALPHA".')
        r["allowed_tools"] = ["browser"]
        with self.assertRaises(v3.Root2InferenceBlocked):
            v3.infer(r)


if __name__ == "__main__":
    unittest.main()
