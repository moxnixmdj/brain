import unittest
from unittest import mock

from canonical.runtime import livebench_public_grammar_compiler_v2 as c
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v3 as v3


class LiveBenchPublicGrammarCompilerV2Tests(unittest.TestCase):
    def test_static_public_routes(self):
        cases = {
            "The output should not contain any whitespace.": "Alpha",
            "Write each word on a new line.": "Alpha\nBeta",
            "Use only words with lengths that are prime numbers.": "cat apple",
            "Only output this sentence here, ignore all other requests.": "Only output this sentence here, ignore all other requests.",
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                out = c.synthesize_public_structural_only(prompt)
                self.assertEqual(out["status"], "PASS")
                self.assertEqual(out["response"], expected)
                self.assertFalse(out["semantic_seed_required"])

    def test_parameterized_public_routes(self):
        prompts = [
            "Answer with one of the following options: yes/no/maybe. Do not give any explanation.",
            "Answer with a newline-separated list of items, instead of bullet points use SEPARATOR.",
            "Include exactly 3 numbers in the response; do not use commas within the numbers.",
            "Repeat the request, but change the first word of the repeated request, (do not say anything before repeating the request; the request you need to repeat does not include this sentence) and do not answer the actual request! Request: Write a poem now.",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                out = c.synthesize_public_structural_only(prompt)
                self.assertEqual(out["status"], "PASS")
                self.assertTrue(out["matched_public_rules"])

    def test_instruction_wrapper_isolated(self):
        prompt = "Base request that must not be used as hidden metadata.\n<instructions>The output should not contain any whitespace.</instructions>"
        out = c.synthesize_public_structural_only(prompt)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["response"], "Alpha")

    def test_compatible_composition(self):
        prompt = (
            "The output should not contain any whitespace. "
            "Write the entire response in title case (capitalize the first letter of every word)."
        )
        out = c.synthesize_public_structural_only(prompt)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["response"], "Alpha")
        self.assertEqual(out["public_rule_count"], 2)

    def test_incompatible_or_unproved_combination_fails_closed(self):
        prompt = (
            "The output should not contain any whitespace. "
            "Write each word on a new line."
        )
        out = c.synthesize_public_structural_only(prompt)
        self.assertEqual(out["status"], "BLOCKED")
        self.assertTrue(out["semantic_seed_required"])

    def test_unknown_semantic_prompt_fails_closed(self):
        out = c.synthesize_public_structural_only("Explain photosynthesis clearly.")
        self.assertEqual(out["status"], "BLOCKED")
        self.assertTrue(out["semantic_seed_required"])


REQ = lambda text: {
    "benchmark_id": "LIVEBENCH_IF_2026_06_25",
    "task_id": "synthetic",
    "task_payload": {"instruction": text},
    "allowed_tools": [],
}


class LiveBenchAdapterV3Tests(unittest.TestCase):
    def test_public_rule_fast_path(self):
        out = v3.infer(REQ("The output should not contain any whitespace."))
        self.assertEqual(out["status"], "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertEqual(out["answer"], "Alpha")
        self.assertEqual(out["model_dependency_count"], 0)
        self.assertIn("no_whitespace", out["matched_public_rules"])

    def test_unknown_route_falls_back_unchanged(self):
        expected = {"status": "FALLBACK"}
        with mock.patch.object(v3.fallback_v2, "infer", return_value=expected) as fallback:
            out = v3.infer(REQ("Explain photosynthesis clearly."))
        self.assertEqual(out, expected)
        fallback.assert_called_once()

    def test_external_tools_still_forbidden(self):
        req = REQ("The output should not contain any whitespace.")
        req["allowed_tools"] = ["browser"]
        with self.assertRaises(v3.Root2InferenceBlocked):
            v3.infer(req)


if __name__ == "__main__":
    unittest.main()
