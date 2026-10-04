import unittest

from canonical.runtime import livebench_if_public_description_inverter_v1 as inv


class PublicDescriptionInverterTests(unittest.TestCase):
    def test_all_58_modern_ids_have_source_or_alias_grammar(self):
        ids = set(inv._TEMPLATES) | set(inv._ALIAS_PATTERNS)
        self.assertEqual(len(ids), 58)
        self.assertTrue(all(inv._TEMPLATES.get(i) or inv._ALIAS_PATTERNS.get(i) for i in ids))

    def test_two_constraints_are_recovered_without_hidden_metadata(self):
        prompt = (
            "Explain the topic. "
            "Include exactly 3 numbers in the response. "
            "Use at least 7 unique words in the response."
        )
        matches = {m["instruction_id"]: m for m in inv.recognize(prompt)}
        self.assertIn("count:numbers", matches)
        self.assertIn("count:unique_word_count", matches)
        self.assertEqual(matches["count:numbers"]["slots"]["N"], "3")
        self.assertEqual(matches["count:unique_word_count"]["slots"]["N"], "7")

    def test_public_ordinal_variant_recovers_position_slots(self):
        prompt = (
            "Include keyword giggle in the 22-nd sentence, "
            "as the 33-rd word of that sentence. Reference Text: test"
        )
        matches = {m["instruction_id"]: m for m in inv.recognize(prompt)}
        got = matches["words:keywords_specific_position"]["slots"]
        self.assertEqual(got, {"keyword": "giggle", "n": "22", "m": "33"})

    def test_repeat_change_recovers_visible_prefix_as_repeat_source(self):
        base = "Write a small deterministic parser."
        prompt = (
            base + " Repeat the request, but change the first word of the repeated request, "
            "(do not say anything before repeating the request; the request you need to repeat "
            "does not include this sentence) and do not answer the actual request!"
        )
        matches = {m["instruction_id"]: m for m in inv.recognize(prompt)}
        self.assertEqual(
            matches["repeat:repeat_change"]["slots"]["prompt_to_repeat"],
            base,
        )

    def test_public_wording_compatibility_aliases(self):
        prompts = {
            "ratio:sentence_balance":
                "Ensure that the ratio of sentence types (declarative, interrogative, exclamatory) "
                "in your response is balanced. Base task.",
            "ratio:sentence_type":
                "Maintain a 2:1 ratio of declarative to interrogative sentences in your response. Base task.",
            "sentence:increment":
                "Each sentence in your response must contain exactly 4 more words than the previous one. Base.",
            "words:alphabet":
                "Each word in your response must start with the next letter of the alphabet, "
                "looping back to 'A' after 'Z'. Base.",
            "words:paragraph_last_first":
                "Each paragraph of your response must end with the same word it started with, "
                "separate paragraphs with a newline. Base.",
        }
        for expected, prompt in prompts.items():
            with self.subTest(expected=expected):
                self.assertIn(expected, {m["instruction_id"] for m in inv.recognize(prompt)})

    def test_options_variant_without_explanation_suffix(self):
        prompt = (
            "Answer with one of the following options: yes/no/maybe. "
            "Could the base question be answered?"
        )
        matches = {m["instruction_id"]: m for m in inv.recognize(prompt)}
        self.assertEqual(matches["format:options"]["slots"]["options"], "yes/no/maybe")

    def test_unrelated_semantic_text_does_not_invent_instruction(self):
        self.assertEqual(inv.recognize("Explain photosynthesis clearly and concisely."), [])

    def test_audit_counts_expected_ids_without_kwargs(self):
        rows = [
            {
                "key": "a",
                "prompt": "Include exactly 2 numbers in the response. Base.",
                "instruction_id_list": ["count:numbers"],
            },
            {
                "key": "b",
                "prompt": "The output should not contain any whitespace. Base.",
                "instruction_id_list": ["format:no_whitespace"],
            },
        ]
        audit = inv.audit_public_rows(rows)
        self.assertEqual(audit["instruction_instance_count"], 2)
        self.assertEqual(audit["recognized_instruction_instances"], 2)
        self.assertEqual(audit["recognition_rate"], 1.0)
        self.assertEqual(audit["failures"], [])


if __name__ == "__main__":
    unittest.main()
