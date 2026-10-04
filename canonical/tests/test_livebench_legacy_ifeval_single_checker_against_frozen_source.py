import os
import pathlib
import sys
import unittest

from canonical.runtime import livebench_legacy_ifeval_description_inverter_v1 as inv
from canonical.runtime import livebench_legacy_ifeval_single_checker_witness_v1 as wit

ROOT = pathlib.Path(os.environ["LIVEBENCH_SOURCE_ROOT"]).resolve()
sys.path.insert(0, str(ROOT / "livebench" / "if_runner"))
from instruction_following_eval import instructions_registry  # noqa: E402

CASES = {
    "keywords:existence": {"keywords": ["alpha", "beta"]},
    "keywords:frequency": {"keyword": "alpha", "frequency": 3, "relation": "at least"},
    "keywords:forbidden_words": {"forbidden_words": ["gamma", "delta"]},
    "keywords:letter_frequency": {"letter": "q", "let_frequency": 4, "let_relation": "at least"},
    "language:response_language": {"language": "en"},
    "length_constraints:number_sentences": {"num_sentences": 3, "relation": "at least"},
    "length_constraints:number_paragraphs": {"num_paragraphs": 3},
    "length_constraints:number_words": {"num_words": 8, "relation": "at least"},
    "length_constraints:nth_paragraph_first_word": {
        "num_paragraphs": 3, "nth_paragraph": 2, "first_word": "orchid"
    },
    "detectable_content:number_placeholders": {"num_placeholders": 3},
    "detectable_content:postscript": {"postscript_marker": "P.S."},
    "detectable_format:number_bullet_lists": {"num_bullets": 3},
    "detectable_format:constrained_response": {},
    "detectable_format:number_highlighted_sections": {"num_highlights": 2},
    "detectable_format:multiple_sections": {"section_spliter": "Section", "num_sections": 3},
    "detectable_format:json_format": {},
    "detectable_format:title": {},
    "combination:two_responses": {},
    "combination:repeat_prompt": {"prompt_to_repeat": "Explain photosynthesis."},
    "startend:end_checker": {"end_phrase": "Any other questions?"},
    "change_case:capital_word_frequency": {"capital_frequency": 4, "capital_relation": "at least"},
    "change_case:english_capital": {},
    "change_case:english_lowercase": {},
    "punctuation:no_comma": {},
    "startend:quotation": {},
}


class FrozenLegacySingleCheckerWitnessVerification(unittest.TestCase):
    def test_exact_active_registry_has_same_25_ids(self):
        self.assertEqual(set(instructions_registry.INSTRUCTION_DICT), inv.LEGACY_IDS)
        self.assertEqual(set(CASES), inv.LEGACY_IDS)

    def test_each_source_rendered_description_inverts_and_witness_passes_exact_checker(self):
        only_id = os.environ.get("ONLY_ID")
        cases = CASES.items() if not only_id else [(only_id, CASES[only_id])]
        for instruction_id, kwargs in cases:
            with self.subTest(instruction_id=instruction_id):
                cls = instructions_registry.INSTRUCTION_DICT[instruction_id]
                checker = cls(instruction_id)
                description = checker.build_description(**kwargs)
                visible_prompt = description
                if instruction_id == "combination:repeat_prompt":
                    visible_prompt = kwargs["prompt_to_repeat"] + " " + description

                matches = inv.recognize(visible_prompt)
                by_id = {m["instruction_id"]: m for m in matches}
                self.assertIn(instruction_id, by_id)
                response = wit.witness_for_match(by_id[instruction_id])
                self.assertIsInstance(response, str)
                self.assertTrue(response.strip())
                self.assertTrue(
                    checker.check_following(response),
                    msg=f"{instruction_id} rejected witness: {response!r}",
                )


if __name__ == "__main__":
    unittest.main()
