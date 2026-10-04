import unittest

from canonical.runtime.ifeval_repeat_prompt_visible_segmenter_v1 import (
    RepeatPromptSegmentationError,
    recover,
    response_prefix_witness,
)


class RepeatPromptVisibleSegmenterTests(unittest.TestCase):
    def test_prefix_form(self):
        prompt = (
            "Write a concise note about trees.\n"
            "First repeat the request word for word without change, then give your answer."
        )
        out = recover(prompt)
        self.assertEqual(out["prompt_to_repeat"], "Write a concise note about trees.")
        self.assertEqual(out["route"], "VISIBLE_PREFIX_BEFORE_REPEAT_DIRECTIVE")

    def test_suffix_form(self):
        prompt = (
            "First repeat the request below word for word without change, then answer.\n\n"
            "Write a concise note about trees."
        )
        out = recover(prompt)
        self.assertEqual(out["prompt_to_repeat"], "Write a concise note about trees.")
        self.assertEqual(out["route"], "VISIBLE_FINAL_LINE_AFTER_REPEAT_DIRECTIVE")

    def test_public_typo_variant(self):
        prompt = (
            "Rewrite this sentence formally.\n\n"
            "Please repleat the entire first line above, then give your rewrite."
        )
        out = recover(prompt)
        self.assertEqual(out["prompt_to_repeat"], "Rewrite this sentence formally.")

    def test_prefix_witness_starts_with_exact_request(self):
        prompt = (
            "Name a fictional planet.\n"
            "Repeat the request above exactly before answering."
        )
        out = response_prefix_witness(prompt)
        self.assertTrue(out["response"].startswith(out["prompt_to_repeat"]))

    def test_ambiguous_multiline_prefix_fails_closed(self):
        prompt = (
            "Line one of request.\n"
            "Line two of request.\n"
            "Repeat the request above exactly."
        )
        with self.assertRaises(RepeatPromptSegmentationError):
            recover(prompt)

    def test_no_directive_fails_closed(self):
        with self.assertRaises(RepeatPromptSegmentationError):
            recover("Write a concise note about trees.")


if __name__ == "__main__":
    unittest.main()
