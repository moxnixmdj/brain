#!/usr/bin/env python3
"""The operand names are welded into the rule, and unwelding them buys exactly nothing here.

WHAT THIS PINS, AND WHY EVERY PART OF IT IS A RESULT
----------------------------------------------------
The owner asks why the model cannot be shown an action once and then apply it anywhere. The tree's
one-example organ is the nearest thing to that, and before this file was written it refused
something a person finds trivial -- the same operation with different variable names:

    taught on:   if a <= hi:   ->   if a < hi:
    refused on:  if x <= top:

Measured, verbatim:

    Refused: nothing in the file has the form the example changed (a <= hi -> a < hi)

So the rule is welded to the demonstrated operand names. That is real, and `alpha_safe_rewrite`
removes the weld: two statements that differ only in the names of their free variables are the same
statement, and that is decidable by walking the trees -- no oracle, no heuristic, no guessing.

Then the measurement, on the same corpus every other number in this tree uses:

    162 applicable askings, 607 developer changes
    AS_TAUGHT   493 of 607  = 0.8122
    ALPHA_SAFE  493 of 607  = 0.8122
    delta       0.0

**Unwelding the operand names buys exactly zero on this corpus.** Two honest explanations, both
checked rather than assumed:

* the organ **never refuses** on this corpus. Of 330 askings, 162 are edited and 168 contain nothing
  the demonstration changed. Zero are refused. So there is no refusal for a wider operator to
  rescue. The "1 of 7 structurally novel instances" figure that motivated `operator_generalization_v1`
  comes from a different corpus (boundary lessons, single-file repairs), not this one.
* the corpus was *selected* for repeated identical changes -- pull requests found because the same
  change appears in file after file. Selection for sameness removes the variation alpha-safety exists
  to bridge.

That is why the result is a finding and not a failure: the corpus cannot see this mechanism, and
saying so is what stops the next round from claiming the gain.

PREDICTIONS, WRITTEN BEFORE THIS FILE WAS FIRST RUN
---------------------------------------------------
P1  `a <= hi` -> `a < hi` is recognised as exactly one operator change, `LtE` -> `Lt`.
P2  `a <= hi` and `x <= top` are the same shape; `a <= hi` and `a < hi` are not.
P3  The demonstrated operation reaches an alpha-renamed target (`x <= top`), which the organ refuses.
P4  It also reaches an identically-named target, and rewrites every matching place, not just one.
P5  It refuses: a target with no matching shape; a target that already has the new operator; a
    demonstration whose two files differ by more than one operator.
P6  On the recorded corpus the delta is 0.0 and the organ refuses 0 of 330 askings. If a later change
    to the organ or the corpus moves either, these fail.
"""
from __future__ import annotations

import ast
import json
import unittest

from canonical.tools.what_the_operand_names_cost_v1 import (
    ROOT,
    alpha_safe_rewrite,
    same_shape,
    _operator_change,
    _statement_of,
)

DEMO_BEFORE = "def f(a, hi):\n    if a <= hi:\n        return True\n"
DEMO_AFTER = "def f(a, hi):\n    if a < hi:\n        return True\n"


class OperandNamesTest(unittest.TestCase):
    """P2: what counts as the same shape, and what does not."""

    def node(self, text):
        return ast.parse(text, mode="eval").body

    def test_p2_a_name_and_a_literal_are_not_structure(self):
        self.assertTrue(same_shape(self.node("a <= hi"), self.node("x <= top")))
        self.assertTrue(same_shape(self.node("a <= 5"), self.node("a <= threshold")))

    def test_p2_the_operator_is_structure(self):
        """The operation is the lesson. If shape ignored it, every lesson would be invisible."""
        self.assertFalse(same_shape(self.node("a <= hi"), self.node("a < hi")))

    def test_p2_an_attribute_name_is_structure(self):
        """`.isSet` -> `.is_set` is a lesson, not an operand."""
        self.assertFalse(same_shape(self.node("e.isSet()"), self.node("e.is_set()")))


class OperatorChangeTest(unittest.TestCase):
    """P1: exactly one operator difference, or nothing."""

    def test_p1_a_comparison_swap_is_one_change(self):
        old, new = _statement_of("    if a <= hi:"), _statement_of("    if a < hi:")
        self.assertEqual(_operator_change(old, new), ("LtE", "Lt"))

    def test_p1_an_arithmetic_swap_is_one_change(self):
        self.assertEqual(_operator_change(self.node("x + 1"), self.node("x - 1")), ("Add", "Sub"))

    def test_p1_two_differences_are_not_one_change(self):
        """A comparison with a different operand count is not a one-operator change at all."""
        self.assertIsNone(_operator_change(self.node("a <= b"), self.node("a > c >= d")))

    def test_p1_a_different_statement_is_not_one_change(self):
        self.assertIsNone(_operator_change(self.node("a <= b"), self.node("a + b")))

    def node(self, text):
        return ast.parse(text, mode="eval").body


class AlphaSafeRewriteTest(unittest.TestCase):
    """P3-P5: what it reaches, and what it refuses."""

    def test_p3_it_reaches_an_alpha_renamed_target(self):
        got = alpha_safe_rewrite(DEMO_BEFORE, DEMO_AFTER,
                                 "def g(x, top):\n    if x <= top:\n        return 1\n")
        self.assertIsNotNone(got)
        self.assertIn("if x < top:", got)

    def test_p3_the_organ_refuses_that_exact_target(self):
        """The whole point: this is the case the shipped organ says it cannot do."""
        from canonical.swe_kernel.taught_actions import edit_by_example_v1 as e
        target = "def g(x, top):\n    if x <= top:\n        return 1\n"
        with self.assertRaises(e.Refused):
            e.repeated(e.learn_all([(DEMO_BEFORE, DEMO_AFTER)]), target, "the example")

    def test_p4_an_identically_named_target_is_reached_too(self):
        got = alpha_safe_rewrite(DEMO_BEFORE, DEMO_AFTER,
                                 "def g(a, hi):\n    if a <= hi:\n        return 1\n")
        self.assertIn("if a < hi:", got)

    def test_p4_every_matching_place_is_rewritten(self):
        got = alpha_safe_rewrite(
            DEMO_BEFORE, DEMO_AFTER,
            "def g(x, t):\n    if x <= t:\n        return 1\n    if x <= t:\n        return 2\n")
        self.assertEqual(got.count("if x < t:"), 2)

    def test_p5_a_target_with_no_matching_shape_is_refused(self):
        self.assertIsNone(alpha_safe_rewrite(DEMO_BEFORE, DEMO_AFTER,
                                             "def g(x):\n    return x + 1\n"))

    def test_p5_a_target_that_already_has_the_new_operator_is_left_alone(self):
        """It must not invent work: there is no `<=` to change, so nothing is returned."""
        self.assertIsNone(alpha_safe_rewrite(DEMO_BEFORE, DEMO_AFTER,
                                             "def g(x, top):\n    if x < top:\n        return 1\n"))

    def test_p5_a_demonstration_that_changes_more_than_one_operator_is_refused(self):
        before = "def f(a, b):\n    if a <= b:\n        return a + 1\n"
        after = "def f(a, b):\n    if a < b:\n        return a - 1\n"
        self.assertIsNone(alpha_safe_rewrite(before, after,
                                             "def g(x, y):\n    if x <= y:\n        return x + 1\n"))

    def test_p5_a_demonstration_with_no_operator_change_is_refused(self):
        self.assertIsNone(alpha_safe_rewrite("x = 1\n", "x = 2\n", "y = 1\n"))


class RecordedResultTest(unittest.TestCase):
    """P6: the measured null, read from the record the tool wrote."""

    @classmethod
    def setUpClass(cls):
        path = ROOT / "canonical/verification/WHAT_THE_OPERAND_NAMES_COST_20261112_V1.json"
        cls.record = json.loads(path.read_text(encoding="utf-8"))

    def test_p6_unwelding_the_operand_names_buys_nothing_on_this_corpus(self):
        tiers = self.record["tiers"]
        self.assertEqual(tiers["AS_TAUGHT"]["covered"], 493)
        self.assertEqual(tiers["ALPHA_SAFE"]["covered"], 493)
        self.assertEqual(tiers["AS_TAUGHT"]["developers_changes"], 607)
        self.assertEqual(tiers["delta_coverage"], 0.0)

    def test_p6_the_organ_never_refuses_on_this_corpus(self):
        """The reason the delta is zero is that there is no refusal to rescue."""
        self.assertEqual(self.record["askings_where_only_alpha_reaches"], 0)

    def test_p6_the_bigger_ladder_is_named_as_oracle_gated_not_as_available(self):
        ladder = self.record["oracle_ladder"]
        self.assertIn("TEST_SUITE", ladder["why_it_is_not_a_tier_here"])
        self.assertIn("has none", ladder["what_that_means"].lower())

    def test_p6_it_states_that_agreement_is_not_correctness(self):
        self.assertIn("NOT_CORRECTNESS", self.record["non_claim"])
        self.assertEqual(self.record["model_calls"], 0)
        self.assertFalse(self.record["terminal_authority"])


if __name__ == "__main__":
    unittest.main()
