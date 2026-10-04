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


class LiveBenchAdapterV3Tests(unittest.TestCase):
    def test_exact_literal_witness(self):
        out = v3.infer(req('Reply with exactly "ALPHA".'))
        self.assertEqual(out["status"], "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertEqual(out["answer"], "ALPHA")
        self.assertEqual(out["response_route"], "LIVEBENCH_VISIBLE_PROMPT_FORMAL_WITNESS_V1")
        self.assertEqual(out["model_dependency_count"], 0)
        self.assertFalse(out["hidden_instruction_metadata_used"])

    def test_structural_word_floor_is_no_longer_discarded(self):
        with mock.patch.object(v3.fallback_v1, "infer") as fallback:
            out = v3.infer(req("Use at least 5 unique words in the response."))
        self.assertEqual(out["status"], "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertGreaterEqual(len(set(out["answer"].lower().split())), 5)
        self.assertEqual(
            out["compiler_status"],
            "FORMAL_CONSTRAINTS_SATISFIED_SEMANTIC_SEED_STILL_REQUIRED",
        )
        fallback.assert_not_called()

    def test_exact_numbers_witness(self):
        with mock.patch.object(v3.fallback_v1, "infer") as fallback:
            out = v3.infer(req("Use exactly 5 words and include exactly 2 numbers."))
        self.assertEqual(out["status"], "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertEqual(len(out["answer"].split()), 5)
        fallback.assert_not_called()

    def test_unrecognized_semantic_prompt_preserves_v1_fallback(self):
        expected = {"status": "FALLBACK_SENTINEL"}
        with mock.patch.object(v3.fallback_v1, "infer", return_value=expected) as fallback:
            out = v3.infer(req("Explain photosynthesis clearly."))
        self.assertEqual(out, expected)
        fallback.assert_called_once()

    def test_contradiction_preserves_v1_fallback(self):
        expected = {"status": "FALLBACK_SENTINEL"}
        with mock.patch.object(v3.fallback_v1, "infer", return_value=expected) as fallback:
            out = v3.infer(req('Reply with exactly "ALPHA". Use lowercase only.'))
        self.assertEqual(out, expected)
        fallback.assert_called_once()

    def test_external_tools_still_forbidden(self):
        r = req('Reply with exactly "ALPHA".')
        r["allowed_tools"] = ["browser"]
        with self.assertRaises(v3.Root2InferenceBlocked):
            v3.infer(r)


if __name__ == "__main__":
    unittest.main()
