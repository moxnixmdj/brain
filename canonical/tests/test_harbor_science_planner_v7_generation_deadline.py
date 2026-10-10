from __future__ import annotations

import math
import unittest

from canonical.runtime import harbor_science_planner_v7 as p


class PlannerV7GenerationDeadlineTests(unittest.TestCase):
    def test_rank18_exact_timeout_bug_is_closed(self):
        # Rank18's exact request had about 3,102 input tokens. V6 allocated
        # ceil(3102/15)+180 == 387s and the public server cancelled all three
        # exact retries at about 388-389s while generation was still healthy.
        self.assertEqual(math.ceil(3102 / 15) + 180, 387)
        self.assertEqual(p.effective_timeout_s(3102, 300), 1753)
        self.assertGreater(p.effective_timeout_s(3102, 300), 3 * 387)

    def test_timeout_accounts_for_entire_bounded_completion(self):
        generation_seconds = math.ceil(
            p.MAX_TOOL_COMPLETION_TOKENS / p.GENERATION_TOKENS_PER_SECOND_FLOOR
        )
        self.assertEqual(generation_seconds, 1366)
        expected = math.ceil(3102 / p.PREFILL_TOKENS_PER_SECOND_FLOOR) + generation_seconds + p.GENERATION_AND_TRANSPORT_MARGIN_S
        self.assertEqual(p.effective_timeout_s(3102, 300), expected)

    def test_short_context_cap_covers_max_short_context_request(self):
        expected = (
            math.ceil(8192 / p.PREFILL_TOKENS_PER_SECOND_FLOOR)
            + math.ceil(p.MAX_TOOL_COMPLETION_TOKENS / p.GENERATION_TOKENS_PER_SECOND_FLOOR)
            + p.GENERATION_AND_TRANSPORT_MARGIN_S
        )
        self.assertEqual(expected, 2093)
        self.assertLessEqual(expected, p.MAX_TIMEOUT_S)
        self.assertEqual(p.effective_timeout_s(8192, 300), expected)

    def test_long_context_cap_covers_full_production_envelope(self):
        max_input = p.SERVER_CONTEXT_TOKENS - p.MAX_TOOL_COMPLETION_TOKENS - 1
        expected = (
            math.ceil(max_input / p.LONG_CONTEXT_PREFILL_TOKENS_PER_SECOND_FLOOR)
            + math.ceil(p.MAX_TOOL_COMPLETION_TOKENS / p.GENERATION_TOKENS_PER_SECOND_FLOOR)
            + p.LONG_CONTEXT_GENERATION_AND_TRANSPORT_MARGIN_S
        )
        self.assertEqual(max_input, 12287)
        self.assertEqual(expected, 3142)
        self.assertLessEqual(expected, p.LONG_CONTEXT_MAX_TIMEOUT_S)
        self.assertEqual(p.effective_timeout_s(max_input, 300), expected)

    def test_generation_floor_has_headroom_below_rank18_observed_rate(self):
        # Public Rank18 logs stayed around 4.48-4.61 tok/s before cancellation.
        self.assertEqual(p.GENERATION_TOKENS_PER_SECOND_FLOOR, 3)
        self.assertLess(p.GENERATION_TOKENS_PER_SECOND_FLOOR, 4.48)

    def test_requested_timeout_validation_stays_bounded(self):
        with self.assertRaisesRegex(Exception, "TIMEOUT_INVALID"):
            p.effective_timeout_s(1000, p.MAX_TIMEOUT_S + 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
