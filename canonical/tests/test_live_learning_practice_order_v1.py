#!/usr/bin/env python3
"""Practice must be chosen by what it is worth, not by a fixed rotation.

The owner rejected "do 1, 2, 3 and that's it". The live learning cycle was
exactly that:

    gens[i % len(gens)]

Four generators, same order, forever -- practising the same quarter of its
repertoire whether or not that is where it is weak. Ordering now comes from
earned value.

No rule says "practise what you fail at". It falls out of the credit signal:
a case the oracle rejects means time there paid off, a case passed easily
taught nothing, and the ledger reorders itself accordingly.
"""

from __future__ import annotations

import os
import tempfile
import unittest

from execution_guard import live_learning_cycle_v1 as llc

FAMILIES = ["math_numeric_sympy", "json_query_jq",
            "python_fault_localize", "python_ast_patch_search"]


class PracticeOrderTests(unittest.TestCase):
    def setUp(self) -> None:
        from canonical.runtime import ignorance_ledger_v1 as led
        self.led = led
        self._real = led.DEFAULT_STATE
        self.tmp = tempfile.mkdtemp(prefix="brain-practice-")
        led.DEFAULT_STATE = os.path.join(self.tmp, "ledger.json")

    def tearDown(self) -> None:
        self.led.DEFAULT_STATE = self._real
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _rounds(self, failing: str, passing: str, n: int = 6) -> None:
        for _ in range(n):
            llc._credit_practice([{"family": failing, "oracle_pass": False},
                                  {"family": passing, "oracle_pass": True}])

    # --- it is not a fixed rotation -------------------------------------------

    def test_all_families_are_always_returned(self):
        """Reordering must never drop anything -- only change the order."""
        order = llc._practice_order(FAMILIES)
        self.assertEqual(sorted(order), sorted(FAMILIES))

    def test_order_responds_to_outcomes(self):
        """The whole point: the sequence is not fixed, it is earned."""
        before = llc._practice_order(FAMILIES)
        self._rounds(failing="math_numeric_sympy", passing="json_query_jq")
        after = llc._practice_order(FAMILIES)
        self.assertNotEqual(before, after)

    # --- it practises what it is weak at --------------------------------------

    def test_a_failing_family_rises_to_the_front(self):
        self._rounds(failing="math_numeric_sympy", passing="json_query_jq")
        order = llc._practice_order(FAMILIES)
        self.assertEqual(order[0], "math_numeric_sympy", order)

    def test_a_family_it_has_mastered_sinks(self):
        self._rounds(failing="math_numeric_sympy", passing="json_query_jq")
        order = llc._practice_order(FAMILIES)
        self.assertEqual(order[-1], "json_query_jq", order)

    def test_sustained_failure_beats_occasional_failure(self):
        for _ in range(8):
            llc._credit_practice([{"family": "python_fault_localize",
                                   "oracle_pass": False}])
        llc._credit_practice([{"family": "math_numeric_sympy",
                               "oracle_pass": False}])
        order = llc._practice_order(FAMILIES)
        self.assertEqual(order[0], "python_fault_localize", order)

    # --- safety ---------------------------------------------------------------

    def test_unknown_families_are_appended_not_lost(self):
        order = llc._practice_order(["brand_new_thing"])
        self.assertEqual(order, ["brand_new_thing"])

    def test_missing_family_on_a_row_is_ignored(self):
        llc._credit_practice([{"oracle_pass": False}])   # no family key
        llc._credit_practice([{"family": "", "oracle_pass": True}])
        self.assertEqual(sorted(llc._practice_order(FAMILIES)), sorted(FAMILIES))

    def test_a_broken_ledger_does_not_stop_practice(self):
        """Keeping score about practice must never prevent practice."""
        self.led.DEFAULT_STATE = "/nonexistent/deeply/broken/path.json"
        try:
            order = llc._practice_order(FAMILIES)
            self.assertEqual(sorted(order), sorted(FAMILIES))
            llc._credit_practice([{"family": "x", "oracle_pass": False}])
        finally:
            self.led.DEFAULT_STATE = os.path.join(self.tmp, "ledger.json")

    def test_empty_rows_are_harmless(self):
        llc._credit_practice([])


if __name__ == "__main__":
    unittest.main()
