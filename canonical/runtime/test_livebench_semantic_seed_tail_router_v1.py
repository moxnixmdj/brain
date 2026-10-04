#!/usr/bin/env python3
import unittest
from unittest import mock

from canonical.runtime import livebench_semantic_seed_tail_router_v1 as router


class SemanticSeedTailRouterTests(unittest.TestCase):
    def test_isolates_complete_multi_sentence_formal_suffix(self):
        text = (
            "Explain photosynthesis briefly. "
            "Answer with at least 5 words. "
            "Response must start with \"BEGIN\"."
        )
        out = router.isolate_formal_tail(text)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["semantic_seed_goal"], "Explain photosynthesis briefly.")
        self.assertEqual(out["formal_segment_count"], 2)
        self.assertIn("at least 5 words", out["formal_tail"])
        self.assertIn('start with "BEGIN"', out["formal_tail"])

    def test_does_not_peel_if_nonformal_tail_remains(self):
        text = (
            "Explain photosynthesis briefly. "
            "Answer with at least 5 words. "
            "Be insightful."
        )
        out = router.isolate_formal_tail(text)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["error"], "NO_UNAMBIGUOUS_FORMAL_SUFFIX")

    def test_does_not_peel_constraint_like_text_inside_semantic_sentence(self):
        text = "Explain why the phrase answer with at least 5 words is an awkward instruction."
        out = router.isolate_formal_tail(text)
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_routes_semantic_seed_then_postprocesses_exactly(self):
        request = {
            "task_id": "t1",
            "benchmark_id": router.BENCHMARK_ID,
            "allowed_tools": [],
            "task_payload": (
                "Explain photosynthesis briefly. "
                "Answer with at least 5 words. "
                "Response must start with \"BEGIN\"."
            ),
        }
        seed_result = {
            "task_id": "t1",
            "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
            "answer": "plants convert light into stored chemical energy",
            "artifacts": [],
            "tool_trace": [{"adapter": "bound"}],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
            "response_route": "BASELINE_SEMANTIC_ROUTE",
        }
        with mock.patch.object(router.baseline_v2, "infer", return_value=seed_result) as infer_mock:
            out = router.infer(request)

        self.assertEqual(out["status"], "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertTrue(out["answer"].startswith("BEGIN"))
        self.assertEqual(out["response_route"], "LIVEBENCH_SEMANTIC_SEED_TAIL_ROUTER_V1")
        self.assertEqual(out["model_dependency_count"], 0)
        called_request = infer_mock.call_args.args[0]
        self.assertEqual(called_request["task_payload"], "Explain photosynthesis briefly.")

    def test_unsafe_postprocess_preserves_v2_baseline(self):
        request = {
            "task_id": "t2",
            "benchmark_id": router.BENCHMARK_ID,
            "allowed_tools": [],
            "task_payload": (
                "Name one planet. "
                "Answer with at least 50 words."
            ),
        }
        seed_result = {
            "task_id": "t2",
            "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
            "answer": "Mars",
            "artifacts": [],
            "tool_trace": [],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
            "response_route": "BASELINE_SEMANTIC_ROUTE",
        }
        baseline_result = {
            "task_id": "t2",
            "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
            "answer": "baseline",
            "artifacts": [],
            "tool_trace": [],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
        }
        with mock.patch.object(
            router.baseline_v2,
            "infer",
            side_effect=[seed_result, baseline_result],
        ) as infer_mock:
            out = router.infer(request)

        self.assertEqual(out["answer"], "baseline")
        self.assertEqual(infer_mock.call_count, 2)
        self.assertEqual(infer_mock.call_args_list[0].args[0]["task_payload"], "Name one planet.")
        self.assertEqual(infer_mock.call_args_list[1].args[0], request)

    def test_no_safe_split_delegates_once_to_v2(self):
        request = {
            "task_id": "t3",
            "benchmark_id": router.BENCHMARK_ID,
            "allowed_tools": [],
            "task_payload": "Explain gravity clearly.",
        }
        baseline_result = {
            "task_id": "t3",
            "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
            "answer": "baseline",
            "artifacts": [],
            "tool_trace": [],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
        }
        with mock.patch.object(router.baseline_v2, "infer", return_value=baseline_result) as infer_mock:
            out = router.infer(request)

        self.assertEqual(out, baseline_result)
        infer_mock.assert_called_once_with(request)


if __name__ == "__main__":
    unittest.main()
