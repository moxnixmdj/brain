import unittest
from unittest import mock

from canonical.runtime import root2_livebench_if_astra_inference_adapter_v4 as v4


def req(text):
    return {
        "benchmark_id": "LIVEBENCH_IF_2026_06_25",
        "task_id": "synthetic",
        "task_payload": {"instruction": text},
        "allowed_tools": [],
    }


class LiveBenchAdapterV4Tests(unittest.TestCase):
    def test_paraphrase_uses_local_semantic_route_without_model(self):
        out = v4.infer(
            req(
                "Paraphrase: The system works because the network is available. "
                "Furthermore, the operator can consider the result."
            )
        )
        self.assertEqual(out["status"], "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertEqual(
            out["response_route"],
            "LOCAL_SEMANTIC_TEXT_CORE_V1_PLUS_STRICT_POSTPROCESSOR_V2",
        )
        self.assertEqual(out["semantic_intent"], "paraphrase")
        self.assertEqual(out["model_dependency_count"], 0)
        self.assertEqual(out["learned_parameter_count"], 0)
        self.assertTrue(out["seed_verbatim_preserved"])
        self.assertIn("network", out["answer"].lower())
        self.assertIn("operator", out["answer"].lower())

    def test_simplify_uses_local_semantic_route(self):
        out = v4.infer(
            req(
                "Simplify: Prior to launch, the team utilized approximately 12 sensors "
                "in order to demonstrate that the system had the ability to operate safely."
            )
        )
        self.assertEqual(out["status"], "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertEqual(out["semantic_intent"], "simplify")
        self.assertIn("12", out["answer"])
        self.assertIn("before", out["answer"].lower())
        self.assertIn("used", out["answer"].lower())

    def test_summarize_uses_extractive_local_semantic_route(self):
        out = v4.infer(
            req(
                "Summarize the following passage: "
                "Mars is smaller than Earth. "
                "Its atmosphere is thin. "
                "Robotic missions have studied its surface. "
                "Scientists continue to analyze those observations."
            )
        )
        self.assertEqual(out["status"], "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertEqual(out["semantic_intent"], "summarize")
        self.assertEqual(
            out["semantic_grounding_class"], "EXTRACTIVE_SOURCE_SENTENCE_SUBSET"
        )

    def test_story_is_prompt_grounded(self):
        out = v4.infer(
            req(
                "Write a fictional story about an engineer who discovers that a bridge "
                "sensor has been reporting the wrong value during a storm."
            )
        )
        self.assertEqual(out["status"], "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertEqual(out["semantic_intent"], "story")
        self.assertIn("engineer", out["answer"].lower())
        self.assertIn("bridge sensor", out["answer"].lower())
        self.assertIn("storm", out["answer"].lower())

    def test_supported_public_punctuation_scaffold_preserves_semantic_seed(self):
        instruction = (
            "Rewrite: The team completed the migration because the checks passed. "
            "Use every standard punctuation mark at least once, including semicolons, "
            "colons, and the interrobang (?!"
        )
        out = v4.infer(req(instruction))
        self.assertEqual(out["status"], "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertTrue(out["seed_verbatim_preserved"])
        self.assertIn("IFBENCH_PUNCTUATION_COVER", out["constraint_transforms"])

    def test_unrecognized_semantic_request_falls_through_to_v3(self):
        expected = {"status": "FALLBACK_V3"}
        with mock.patch.object(v4.fallback_v3, "infer", return_value=expected) as f:
            out = v4.infer(req("Explain photosynthesis clearly."))
        self.assertEqual(out, expected)
        f.assert_called_once()

    def test_postprocessor_failure_falls_through_to_v3(self):
        expected = {"status": "FALLBACK_V3"}
        with mock.patch.object(
            v4.semantic_core,
            "produce",
            return_value={
                "status": "PASS",
                "seed": "semantic seed",
                "intent": "paraphrase",
                "grounding_class": "TEST",
                "grounding": {},
            },
        ), mock.patch.object(
            v4.postprocessor, "transform", return_value={"status": "FAIL_CLOSED"}
        ), mock.patch.object(v4.fallback_v3, "infer", return_value=expected) as f:
            out = v4.infer(req("Paraphrase: source material."))
        self.assertEqual(out, expected)
        f.assert_called_once()

    def test_external_tools_remain_forbidden_before_semantic_work(self):
        request = req("Rewrite: The system works.")
        request["allowed_tools"] = ["browser"]
        with self.assertRaises(v4.Root2InferenceBlocked):
            v4.infer(request)

    def test_grader_only_metadata_does_not_create_a_route(self):
        # The evaluated model's ABI is prompt-only. Adding fake scorer metadata
        # to the request must not rescue an unsupported prompt.
        request = req("Explain photosynthesis clearly.")
        request["instruction_id_list"] = ["format:no_whitespace"]
        request["kwargs"] = [{"secret": "grader-only"}]
        expected = {"status": "FALLBACK_V3"}
        with mock.patch.object(v4.fallback_v3, "infer", return_value=expected):
            out = v4.infer(request)
        self.assertEqual(out, expected)


if __name__ == "__main__":
    unittest.main()
