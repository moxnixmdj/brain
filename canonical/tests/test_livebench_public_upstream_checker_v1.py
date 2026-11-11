#!/usr/bin/env python3
from __future__ import annotations

import sys
import types
import unittest

spacy = types.ModuleType("spacy")
spacy.util = types.SimpleNamespace(is_package=lambda _name: True)
spacy_cli = types.ModuleType("spacy.cli")
spacy_cli.download = lambda _name: None
sys.modules.setdefault("spacy", spacy)
sys.modules.setdefault("spacy.cli", spacy_cli)

from livebench.if_runner.ifbench import instructions_registry
from canonical.runtime.livebench_public_constraint_solver_v1 import solve


class FrozenUpstreamModernCheckerSmoke(unittest.TestCase):
    def _check(self, instruction_id, kwargs=None):
        kwargs = dict(kwargs or {})
        cls = instructions_registry.INSTRUCTION_DICT[instruction_id]
        checker = cls(instruction_id)
        description = checker.build_description(**kwargs)
        out = solve(description)
        self.assertEqual(
            out["status"], "WITNESS_CONSTRUCTED",
            {"id": instruction_id, "description": description, "solver": out},
        )
        self.assertTrue(
            checker.check_following(out["response"]),
            {"id": instruction_id, "description": description, "response": out["response"], "solver": out},
        )
        return out

    def test_core_parameterized(self):
        cases = [
            ("count:word_count_range", {"min_words": 5, "max_words": 7}),
            ("count:unique_word_count", {"N": 5}),
            ("count:conjunctions", {"small_n": 4}),
            ("count:person_names", {"N": 6}),
            ("count:numbers", {"N": 3}),
            ("words:repeats", {"small_n": 2}),
            ("sentence:keyword", {"word": "orbit", "N": 2}),
            ("count:pronouns", {"N": 4}),
            ("sentence:increment", {"small_n": 2}),
            ("words:keywords_specific_position", {"keyword": "orbit", "n": 2, "m": 3}),
            ("words:words_position", {"keyword": "orbit"}),
        ]
        for instruction_id, kwargs in cases:
            with self.subTest(instruction_id=instruction_id):
                self._check(instruction_id, kwargs)

    def test_core_fixed(self):
        ids = [
            "ratio:sentence_type",
            "ratio:sentence_balance",
            "words:alphabet",
            "words:vowel",
            "words:consonants",
            "words:palindrome",
            "count:punctuation",
            "format:parentheses",
            "words:prime_lengths",
            "format:newline",
            "ratio:sentence_words",
            "words:odd_even_syllables",
            "words:last_first",
            "words:paragraph_last_first",
            "words:no_consecutive",
            "format:line_indent",
            "format:thesis",
            "format:sub-bullets",
            "format:no_bullets_bullets",
            "custom:multiples",
            "custom:mcq_count_length",
            "custom:reverse_newline",
            "custom:word_reverse",
            "custom:character_reverse",
            "custom:sentence_alphabet",
            "custom:european_capitals_sort",
            "custom:csv_city",
            "custom:csv_special_character",
            "custom:csv_quotes",
            "custom:date_format_list",
            "repeat:repeat_simple",
            "format:title_case",
            "format:output_template",
            "format:no_whitespace",
        ]
        for instruction_id in ids:
            with self.subTest(instruction_id=instruction_id):
                self._check(instruction_id)

    def test_nth_japanese(self):
        self._check("count:words_japanese", {"N": 3})

    def test_options(self):
        self._check("format:options", {"options": "yes/no/maybe"})

    def test_repeat_change(self):
        self._check(
            "repeat:repeat_change",
            {"prompt_to_repeat": "Explain why the sky appears blue"},
        )

    def test_truth_repaired_ratio_overlap_stays_blocked(self):
        cls = instructions_registry.INSTRUCTION_DICT["ratio:overlap"]
        checker = cls("ratio:overlap")
        description = checker.build_description(reference_text="alpha  beta", percentage=40)
        out = solve(description)
        self.assertEqual(out["status"], "BLOCKED", out)
        self.assertIn(
            "RATIO_OVERLAP_EXACT_REFERENCE_TEXT_NOT_PROVED_DERIVABLE",
            out["unsupported"],
        )

    def test_repeat_span_stays_blocked_without_visible_base_binding(self):
        cls = instructions_registry.INSTRUCTION_DICT["repeat:repeat_span"]
        checker = cls("repeat:repeat_span")
        description = checker.build_description(
            prompt_to_repeat="alpha beta gamma delta epsilon",
            n_start=1,
            n_end=3,
        )
        out = solve(description)
        self.assertEqual(out["status"], "BLOCKED", out)
        self.assertIn(
            "REPEAT_SPAN_EXACT_VISIBLE_BASE_SEGMENT_BINDING_NOT_YET_FROZEN",
            out["unsupported"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
