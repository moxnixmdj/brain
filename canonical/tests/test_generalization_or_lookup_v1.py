"""Pin the measurement that decides whether Problem 2 is "exact matches only".

The owner's Problem 2 statement is a factual claim: *generalization is not working, exact matches
only.* This module separates the two abilities on the recorded corpus:

* a change on a statement the example's own file **showed** is recovered by remembering it;
* a change on a statement it **never showed** is recovered only by generalizing.

These tests hold the classification rule, the equivalence rule, and the recorded result. If a later
change to the organ moves any of them, the numbers in the memo go stale and these fail.
"""
from __future__ import annotations

import unittest

from canonical.tools.generalization_or_lookup_v1 import equivalent, classify, _import_key


class ClassifyTest(unittest.TestCase):
    def test_a_statement_the_example_holds_is_looking_up(self):
        showed = {"    logger.warn('x')"}
        change = (3, ("    logger.warn('x')",), ("    logger.warning('x')",))
        self.assertEqual(classify(change, showed), "SHOWED")

    def test_a_statement_the_example_never_held_is_generalizing(self):
        showed = {"    logger.warn('x')"}
        change = (9, ("    log.warn(msg, extra=1)",), ("    log.warning(msg, extra=1)",))
        self.assertEqual(classify(change, showed), "NEVER_SHOWED")

    def test_the_classification_reads_the_old_text_only(self):
        """It must not look at what the organ produced, or it would grade its own answer."""
        change = (1, ("a.old()",), ("a.new()",))
        self.assertEqual(classify(change, set()), "NEVER_SHOWED")
        self.assertEqual(classify(change, {"a.old()"}), "SHOWED")


class EquivalenceTest(unittest.TestCase):
    def test_imported_names_in_another_order_are_the_same_change(self):
        one = (10, ("from datetime import date, datetime, timedelta",),
               ("from datetime import date, datetime, timedelta, UTC",))
        other = (10, ("from datetime import date, datetime, timedelta",),
                 ("from datetime import UTC, date, datetime, timedelta",))
        self.assertTrue(equivalent(one, other), "the same names from the same module")

    def test_a_different_set_of_names_is_not_the_same_change(self):
        one = (10, ("from datetime import datetime",), ("from datetime import UTC, datetime",))
        other = (10, ("from datetime import datetime",), ("from datetime import datetime, timezone",))
        self.assertFalse(equivalent(one, other))

    def test_a_different_module_is_not_the_same_change(self):
        one = (1, ("import os",), ("import os, sys",))
        other = (1, ("import os",), ("import os, re",))
        self.assertFalse(equivalent(one, other))

    def test_code_is_never_excused_by_equivalence(self):
        one = (1, ("x = a.old()",), ("x = a.new()",))
        other = (1, ("x = a.old()",), ("x = b.new()",))
        self.assertFalse(equivalent(one, other))

    def test_never_equivalent_to_a_change_whose_new_side_is_empty(self):
        one = (1, ("import os",), ("import os, sys",))
        self.assertFalse(equivalent(one, (1, ("import os",), ())))

    def test_import_keys_read_names_not_order(self):
        self.assertEqual(_import_key("from a import c, b"), _import_key("from a import b, c"))
        self.assertIsNone(_import_key("x = 1"))


class RecordedResultTest(unittest.TestCase):
    """The numbers the memo quotes, read from the record the tool wrote."""

    @classmethod
    def setUpClass(cls):
        import json
        from canonical.tools.generalization_or_lookup_v1 import ROOT
        path = ROOT / "canonical/verification/GENERALIZATION_OR_LOOKUP_20261112_V1.json"
        cls.record = json.loads(path.read_text(encoding="utf-8"))

    def test_most_of_what_one_showing_recovers_was_never_shown(self):
        """This is the answer to "exact matches only": it is false."""
        self.assertEqual(self.record["recovered_total"], 386)
        self.assertEqual(self.record["recovered_never_showed"], 370)
        self.assertAlmostEqual(
            self.record["share_of_recovered_changes_that_are_generalization"], 0.9585, places=4)

    def test_the_two_populations_are_both_reported(self):
        rows = self.record["lookup_vs_generalization"]
        self.assertEqual(rows["SHOWED"]["right"], 16)
        self.assertEqual(rows["SHOWED"]["missed"], 7)
        self.assertEqual(rows["NEVER_SHOWED_strict"]["right"], 370)
        self.assertEqual(rows["NEVER_SHOWED_strict"]["missed"], 214)

    def test_the_denominator_excludes_askings_no_operator_can_reach(self):
        """168 askings have nothing the example changed, and are counted apart, not in the share."""
        self.assertEqual(self.record["askings_not_applicable"], 168)
        self.assertAlmostEqual(self.record["coverage_strict"], 0.6359, places=4)

    def test_it_states_that_agreement_is_not_correctness(self):
        self.assertIn("NOT_CORRECTNESS", self.record["non_claim"])
        self.assertEqual(self.record["model_calls"], 0)
        self.assertEqual(self.record["incremental_spend_usd"], 0)
        self.assertFalse(self.record["terminal_authority"])


if __name__ == "__main__":
    unittest.main()
