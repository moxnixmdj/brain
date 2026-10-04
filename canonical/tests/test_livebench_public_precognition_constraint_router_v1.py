import unittest
from unittest import mock

from canonical.runtime import livebench_public_precognition_constraint_router_v1 as r


def req(text):
    return {
        "benchmark_id": "LIVEBENCH_IF_2026_06_25",
        "task_id": "synthetic",
        "task_payload": {"instruction": text},
        "allowed_tools": [],
    }


class LiveBenchPreCognitionRouterTests(unittest.TestCase):
    def test_unique_word_suffix_is_removed_before_semantic_cognition(self):
        seen = {}
        def seed(request):
            seen["instruction"] = request["task_payload"]["instruction"]
            return {
                "answer": "photosynthesis converts light into chemical energy",
                "artifacts": [],
                "tool_trace": [],
                "cognition_dependency_class": "MODEL_INDEPENDENT",
                "model_dependency_count": 0,
            }
        text = "Explain photosynthesis. Use at least 10 unique words in the response."
        with mock.patch.object(r.fallback_v1, "infer", side_effect=seed):
            out = r.infer(req(text))
        self.assertEqual(seen["instruction"], "Explain photosynthesis.")
        self.assertTrue(out["constraint_postvalidated"])
        self.assertGreaterEqual(len({x.lower() for x in r._word_tokens(out["answer"])}), 10)
        self.assertEqual(
            out["response_route"],
            "PUBLIC_PRECOGNITION_CONSTRAINT_ROUTER_V1:UNIQUE_WORD_COUNT",
        )

    def test_exact_number_suffix_is_removed_and_projected(self):
        seen = {}
        def seed(request):
            seen["instruction"] = request["task_payload"]["instruction"]
            return {
                "answer": "Provide a compact answer without numerals",
                "artifacts": [],
                "tool_trace": [],
                "cognition_dependency_class": "MODEL_INDEPENDENT",
                "model_dependency_count": 0,
            }
        text = (
            "Describe a triangle. "
            "Include exactly 3 numbers in the response; do not use commas within the numbers."
        )
        with mock.patch.object(r.fallback_v1, "infer", side_effect=seed):
            out = r.infer(req(text))
        self.assertEqual(seen["instruction"], "Describe a triangle.")
        self.assertEqual(len(r.re.findall(r"\\b\\d+\\b", out["answer"])), 3)
        self.assertTrue(out["constraint_postvalidated"])

    def test_seed_with_too_many_numbers_falls_back_to_active_v2(self):
        fallback = {"status": "ACTIVE_V2_FALLBACK"}
        with mock.patch.object(
            r.fallback_v1,
            "infer",
            return_value={
                "answer": "1 2 3 4",
                "cognition_dependency_class": "MODEL_INDEPENDENT",
                "model_dependency_count": 0,
            },
        ), mock.patch.object(r.fallback_v2, "infer", return_value=fallback) as f:
            out = r.infer(
                req(
                    "Summarize this. Include exactly 2 numbers in the response; "
                    "do not use commas within the numbers."
                )
            )
        self.assertEqual(out, fallback)
        f.assert_called_once()

    def test_unrecognized_constraint_falls_through_without_rewriting(self):
        fallback = {"status": "ACTIVE_V2_FALLBACK"}
        with mock.patch.object(r.fallback_v2, "infer", return_value=fallback) as f:
            out = r.infer(req("Explain gravity. Use exactly three paragraphs."))
        self.assertEqual(out, fallback)
        f.assert_called_once()

    def test_external_tools_remain_forbidden(self):
        x = req("Explain gravity. Use at least 4 unique words in the response.")
        x["allowed_tools"] = ["browser"]
        with self.assertRaises(r.PreCognitionRouteBlocked):
            r.infer(x)


if __name__ == "__main__":
    unittest.main()
