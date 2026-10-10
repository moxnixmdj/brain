from __future__ import annotations
import unittest

from canonical.runtime import harbor_science_planner_v6 as p


class PlannerV6GenerationAwareTimeoutTests(unittest.TestCase):
    def test_short_prompt_budgets_reserved_completion_generation(self):
        self.assertEqual(p.MAX_TOOL_COMPLETION_TOKENS, 4096)
        self.assertEqual(p.COMPLETION_TOKENS_PER_SECOND_FLOOR, 8)
        self.assertEqual(p.effective_timeout_s(1000, 180), 759)

    def test_rank18_prompt_no_longer_collapses_to_300_second_floor(self):
        # Exact Rank18 prestart input-token count from the irreversible result truth.
        self.assertEqual(p.effective_timeout_s(2948, 300), 889)

    def test_rank12_class_is_bounded_by_short_context_cap(self):
        self.assertEqual(p.effective_timeout_s(7142, 300), p.MAX_TIMEOUT_S)

    def test_long_context_reserves_slower_completion_generation(self):
        self.assertEqual(p.LONG_CONTEXT_COMPLETION_TOKENS_PER_SECOND_FLOOR, 4)
        self.assertEqual(p.effective_timeout_s(8193, 300), p.LONG_CONTEXT_MAX_TIMEOUT_S)

    def test_invalid_inputs_still_fail_closed(self):
        for input_tokens in (0, -1, True, 1.5):
            with self.subTest(input_tokens=input_tokens):
                with self.assertRaisesRegex(Exception, "INPUT_TOKEN_COUNT_INVALID"):
                    p.effective_timeout_s(input_tokens, 300)
        for timeout_s in (0, p.MAX_TIMEOUT_S + 1, True, 1.5):
            with self.subTest(timeout_s=timeout_s):
                with self.assertRaisesRegex(Exception, "TIMEOUT_INVALID"):
                    p.effective_timeout_s(2948, timeout_s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
