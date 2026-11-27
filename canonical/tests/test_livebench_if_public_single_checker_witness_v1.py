import unittest

from canonical.runtime.livebench_if_public_single_checker_witness_v1 import (
    construct_single_checker_witness as build,
)


class LiveBenchPublicSingleCheckerWitnessV1Tests(unittest.TestCase):
    def test_word_range_parameterized(self):
        out=build("The response must contain between 71 and 73 words. Base request.")
        self.assertEqual(out["status"],"PASS_CANDIDATE")
        self.assertEqual(out["checker_id"],"count:word_count_range")
        self.assertEqual(len(out["response"].split()),71)

    def test_unique_words_parameterized(self):
        out=build("Use at least 9 unique words in the response. Base request.")
        self.assertEqual(out["checker_id"],"count:unique_word_count")
        self.assertEqual(len(set(out["response"].split())),9)

    def test_conjunction_parameterized(self):
        out=build("Use at least 5 different coordinating conjunctions in the response.")
        self.assertEqual(out["response"].split(),["and","but","for","nor","or"])

    def test_person_names_parameterized(self):
        out=build("Mention at least 14 different person names in the response, from this list of person names: Emma, Liam.")
        self.assertEqual(out["checker_id"],"count:person_names")
        self.assertEqual(len(out["response"].split()),14)

    def test_numbers_parameterized(self):
        out=build("Include exactly 15 numbers in the response; do not use commas within the numbers.")
        self.assertEqual(out["checker_id"],"count:numbers")
        self.assertEqual(len(out["response"].split()),15)

    def test_sentence_keyword_parameterized(self):
        out=build("The response must include keyword giraffe in the 7-th sentence.")
        self.assertEqual(out["checker_id"],"sentence:keyword")
        self.assertEqual(len([x for x in out["response"].split(".") if x.strip()]),7)
        self.assertIn("giraffe",out["response"])

    def test_repeat_change_recovers_visible_base(self):
        prompt=(
            "Write a python program. "
            "Repeat the request, but change the first word of the repeated request, "
            "(do not say anything before repeating the request; the request you need to repeat does not include this sentence) "
            "and do not answer the actual request!"
        )
        out=build(prompt)
        self.assertEqual(out["checker_id"],"repeat:repeat_change")
        self.assertEqual(out["response"].split()[1:],["a","python","program."])

    def test_static_verified_boundary_reuse(self):
        out=build("Ensure each word in your response has at least one consonant cluster (two or more consonants together).")
        self.assertEqual(out["checker_id"],"words:consonants")
        self.assertEqual(out["response"],"string plant")

    def test_combination_fails_closed(self):
        out=build("Include exactly 15 numbers in the response. Use at least 5 different coordinating conjunctions in the response.")
        self.assertEqual(out["status"],"BLOCKED")
        self.assertEqual(set(out["matched_checker_ids"]),{"count:numbers","count:conjunctions"})

    def test_unsupported_public_checker_is_recognized_and_blocked(self):
        out=build("Maintain a trigram overlap of 23% (±2%) with the provided reference text. Base request.")
        self.assertEqual(out["status"],"BLOCKED")
        self.assertEqual(out["reason"],"PUBLIC_CHECKER_RECOGNIZED_BUT_CONSTRUCTOR_UNSUPPORTED")
        self.assertEqual(out["matched_checker_ids"],["guard:ratio:overlap"])

    def test_supported_plus_unsupported_conjunction_fails_closed(self):
        out=build(
            "Maintain a trigram overlap of 23% (±2%) with the provided reference text. "
            "The response must include keyword giraffe in the 7-th sentence."
        )
        self.assertEqual(out["status"],"BLOCKED")
        self.assertEqual(
            set(out["matched_checker_ids"]),
            {"guard:ratio:overlap","sentence:keyword"},
        )

    def test_unknown_semantic_prompt_fails_closed(self):
        out=build("Explain photosynthesis clearly.")
        self.assertEqual(out["status"],"BLOCKED")
        self.assertEqual(out["matched_checker_ids"],[])

    def test_model_and_terminal_dependencies_are_zero(self):
        out=build("The output should not contain any whitespace.")
        self.assertEqual(out["status"],"PASS_CANDIDATE")
        self.assertEqual(out["model_dependency_count"],0)
        self.assertFalse(out["terminal_case_content_required"])


if __name__=="__main__":
    unittest.main()
