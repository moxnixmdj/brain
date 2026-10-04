import unittest

from canonical.runtime.ifbench_public_description_grammar_compiler_v1 import (
    combine_grammars,
    compile_grammar,
    recover_visible_bindings,
)


MODERN = r'''
class Instruction: pass

class OptionsResponseChecker(Instruction):
    def build_description(self, *, options=None):
        self._options_text = options
        self._description_pattern = "Answer with one of the following options: {options}. Do not give any explanation."
        return self._description_pattern.format(options=self._options_text)
    def get_instruction_args(self):
        return {"options": self._options_text}
    def get_instruction_args_keys(self):
        return ["options"]

class NGramOverlapChecker(Instruction):
    def build_description(self, *, reference_text=None, percentage=None):
        self._reference_text = reference_text
        self._percentage = percentage
        self._description_pattern = "Maintain a trigram overlap of {percentage}% (±2%) with the provided reference text."
        return self._description_pattern.format(percentage=self._percentage)
    def get_instruction_args(self):
        return {"reference_text": self._reference_text, "percentage": self._percentage}
    def get_instruction_args_keys(self):
        return ["reference_text", "percentage"]

class InactiveChecker(Instruction):
    def build_description(self, *, secret=None):
        self._description_pattern = "Never active {secret}"
        return self._description_pattern.format(secret=secret)
'''

MODERN_REGISTRY = r'''
from x import instructions
INSTRUCTION_DICT = {
    "format:options": instructions.OptionsResponseChecker,
    "ratio:overlap": instructions.NGramOverlapChecker,
}
'''

LEGACY = r'''
class Instruction: pass

class EndChecker(Instruction):
    def build_description(self, *, end_phrase=None):
        self._end_phrase = end_phrase
        self._description_pattern = (
            "Finish your response with this exact phrase {ender}. "
            "No other words should follow this phrase."
        )
        return self._description_pattern.format(ender=self._end_phrase)
    def get_instruction_args(self):
        return {"end_phrase": self._end_phrase}
    def get_instruction_args_keys(self):
        return ["end_phrase"]

class RepeatPromptThenAnswer(Instruction):
    def build_description(self, *, prompt_to_repeat=None):
        self._prompt_to_repeat = prompt_to_repeat
        self._description_pattern = (
            "First repeat the request word for word without change, "
            "then give your answer."
        )
        return self._description_pattern
    def get_instruction_args(self):
        return {"prompt_to_repeat": self._prompt_to_repeat}
    def get_instruction_args_keys(self):
        return ["prompt_to_repeat"]
'''

LEGACY_REGISTRY = r'''
from x import instructions
_PREFIX = "combination:"
_START = "startend:"
INSTRUCTION_DICT = {
    _START + "end_checker": instructions.EndChecker,
    _PREFIX + "repeat_prompt": instructions.RepeatPromptThenAnswer,
}
'''


class PublicDescriptionGrammarCompilerTests(unittest.TestCase):
    def test_filters_registry_and_proves_visible_alias(self):
        manifest = compile_grammar(MODERN, MODERN_REGISTRY)
        self.assertEqual(manifest["active_checker_count"], 2)
        by_id = {x["instruction_id"]: x for x in manifest["checkers"]}
        options = by_id["format:options"]
        self.assertTrue(options["visible_complete"])
        self.assertEqual(options["hidden_parameter_keys"], ())
        self.assertIn(("options", "options"), options["placeholder_to_parameter_key"])

    def test_hidden_parameter_is_not_magically_promoted(self):
        manifest = compile_grammar(MODERN, MODERN_REGISTRY)
        by_id = {x["instruction_id"]: x for x in manifest["checkers"]}
        overlap = by_id["ratio:overlap"]
        self.assertFalse(overlap["visible_complete"])
        self.assertEqual(overlap["hidden_parameter_keys"], ("reference_text",))
        self.assertIn("percentage", overlap["visible_parameter_keys"])

    def test_alias_placeholder_maps_to_canonical_parameter(self):
        manifest = compile_grammar(LEGACY, LEGACY_REGISTRY)
        by_id = {x["instruction_id"]: x for x in manifest["checkers"]}
        end = by_id["startend:end_checker"]
        self.assertTrue(end["visible_complete"])
        self.assertIn(("ender", "end_phrase"), end["placeholder_to_parameter_key"])
        matches = recover_visible_bindings(
            "Do the task. Finish your response with this exact phrase DONE. No other words should follow this phrase.",
            end,
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["recovered_parameters"]["end_phrase"], "DONE")

    def test_true_hidden_legacy_parameter_remains_hidden(self):
        manifest = compile_grammar(LEGACY, LEGACY_REGISTRY)
        by_id = {x["instruction_id"]: x for x in manifest["checkers"]}
        repeat = by_id["combination:repeat_prompt"]
        self.assertFalse(repeat["visible_complete"])
        self.assertEqual(repeat["hidden_parameter_keys"], ("prompt_to_repeat",))

    def test_combined_counts_and_duplicate_firewall(self):
        a = compile_grammar(MODERN, MODERN_REGISTRY)
        b = compile_grammar(LEGACY, LEGACY_REGISTRY)
        combined = combine_grammars(a, b)
        self.assertEqual(combined["active_checker_count"], 4)
        self.assertEqual(combined["visible_complete_count"], 2)
        self.assertEqual(combined["hidden_parameter_checker_count"], 2)


if __name__ == "__main__":
    unittest.main()
