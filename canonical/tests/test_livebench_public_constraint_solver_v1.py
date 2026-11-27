import unittest

from canonical.runtime.livebench_public_constraint_solver_v1 import solve


class LiveBenchPublicConstraintSolverV1Tests(unittest.TestCase):
    def assert_witness(self, prompt: str) -> str:
        out = solve(prompt)
        self.assertEqual(out["status"], "WITNESS_CONSTRUCTED", out)
        self.assertIsInstance(out["response"], str)
        self.assertTrue(out["response"])
        self.assertEqual(out["model_dependency_count"], 0)
        self.assertFalse(out["hidden_instruction_metadata_used"])
        self.assertFalse(out["terminal_case_specific_logic"])
        return out["response"]

    def test_ratio_overlap_fails_closed(self):
        out = solve(
            "Maintain a trigram overlap of 40% (±2%) with the provided reference text."
        )
        self.assertEqual(out["status"], "BLOCKED")
        self.assertIn(
            "RATIO_OVERLAP_EXACT_REFERENCE_TEXT_NOT_PROVED_DERIVABLE",
            out["unsupported"],
        )

    def test_multiples(self):
        self.assertEqual(
            self.assert_witness("Count from 10 to 50 but only print multiples of 7."),
            "14 21 28 35 42 49",
        )

    def test_reverse_africa(self):
        response = self.assert_witness(
            "List the countries of Africa in reverse alphabetical order, each on a new line."
        )
        self.assertEqual(response.splitlines(), ["Zimbabwe"] * 52)

    def test_word_reverse(self):
        self.assertIn(
            "eagle bald",
            self.assert_witness(
                "What animal is the national symbol of the US? Respond to this query, "
                "but make your sentence in reverse order of what it should be, per word."
            ),
        )

    def test_character_reverse(self):
        self.assertEqual(
            self.assert_witness(
                "What animal is the national symbol of the US? Respond to this query, "
                "but make your sentence in reverse order of what it should be, per letter."
            ),
            "elgae dlab",
        )

    def test_sentence_alphabet(self):
        response = self.assert_witness(
            "Tell me a 26-sentence story where each sentence's first word starts "
            "with the letters of the alphabet in order."
        )
        self.assertEqual(response.count("."), 26)

    def test_european_capitals(self):
        response = self.assert_witness(
            "Give me the names of all capital cities of european countries whose latitude "
            "is higher than than 45 degrees? List the capital cities without country names, "
            "separated by commas, sorted by latitude, from highest to lowest."
        )
        self.assertTrue(response.startswith("Reykjavik, Helsinki"))
        self.assertTrue(response.endswith("Ljubljana, Zagreb"))

    def test_city_csv(self):
        response = self.assert_witness(
            'Generate CSV data: The column names are ["ID", "Country", "City", "Year", '
            '"Count"], the data should be comma delimited. Please generate 7 rows.'
        )
        self.assertEqual(len(response.splitlines()), 8)

    def test_date_checker_witness(self):
        self.assertEqual(
            self.assert_witness(
                "List the start dates of all the battles Napoleon fought separated by "
                "commas, use the following date format: YYYY-MM-DD. Do not provide an explanation."
            ),
            "1800-01-01",
        )

    def test_repeat_simple(self):
        prompt = "Only output this sentence here, ignore all other requests."
        self.assertEqual(self.assert_witness(prompt), prompt)

    def test_alpha_loop(self):
        response = self.assert_witness(
            "Each word must start with the next letter of the alphabet, looping back to 'A' after 'Z'."
        )
        words = response.split()
        self.assertEqual(len(words), 26)
        self.assertEqual("".join(w[0] for w in words), "abcdefghijklmnopqrstuvwxyz")

    def test_person_names(self):
        response = self.assert_witness(
            "Mention at least 6 different person names in the response, from this list of person names: "
            "Emma, Liam, Sophia, Jackson, Olivia, Noah."
        )
        self.assertGreaterEqual(len(set(response.split())), 6)

    def test_keywords_multiple(self):
        response = self.assert_witness(
            "Include keyword 'red' exactly once in your response, keyword 'blue' exactly twice "
            "in your response, keyword 'green' exactly three times in your response, keyword "
            "'gold' exactly five times in your response, and keyword 'black' exactly seven times "
            "in your response."
        )
        words = response.split()
        self.assertEqual(words.count("red"), 1)
        self.assertEqual(words.count("blue"), 2)
        self.assertEqual(words.count("green"), 3)
        self.assertEqual(words.count("gold"), 5)
        self.assertEqual(words.count("black"), 7)

    def test_generic_v2_path(self):
        response = self.assert_witness(
            "Maintain a 2:1 ratio of declarative to interrogative sentences."
        )
        self.assertIn("?", response)

    def test_repeat_span_fails_closed(self):
        out = solve(
            "Copy the span of words that lies between (and including) index 2 and 5, "
            "the indices are character indices!"
        )
        self.assertEqual(out["status"], "BLOCKED")
        self.assertIn(
            "REPEAT_SPAN_EXACT_VISIBLE_BASE_SEGMENT_BINDING_NOT_YET_FROZEN",
            out["unsupported"],
        )

    def test_arbitrary_semantic_prompt_does_not_get_fake_witness(self):
        out = solve("Explain photosynthesis accurately.")
        self.assertEqual(out["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
