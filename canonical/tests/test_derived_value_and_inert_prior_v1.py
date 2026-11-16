"""The derived-value algebra and the inert-action prior, tested where they were measured wrong.

Each test here fails if a specific defect that the MiniWoB++ pages produced on 2026-11-16 comes
back. They are not restatements of the implementation; they are the four things that were
actually broken, plus the safety of the two operators that evaluate page text.
"""
from __future__ import annotations

import json
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import derived_value_v1 as dv  # noqa: E402
from canonical.runtime.inert_action_prior_v1 import (  # noqa: E402
    DEFERRED_SURCHARGE, InertActionPrior, classify,
)

PAGE_ARITHMETIC = {
    "utterance": "Solve the math problem and type your answer into the textbox. Press submit.",
    "elements": [
        {"index": 4, "tag": "div", "text": "7 + 0 =", "can_click": True},
        {"index": 5, "tag": "input", "type": "text", "value": "", "can_type": True},
    ],
}
PAGE_ALGEBRA = {
    "utterance": "Solve for x and type your answer into the textbox. Press Submit when done.",
    "elements": [
        {"index": 3, "tag": "div", "text": "8 + x = 33"},
        {"index": 5, "tag": "span", "text": "x ="},
        {"index": 6, "tag": "input", "type": "text", "value": "", "can_type": True},
        {"index": 7, "tag": "button", "text": "Submit", "can_click": True},
    ],
}
#: The regression page: typing the wrong query here makes the page unreachable, and a draft that
#: offered the button's own label ("Search") as a value to type turned a 3-action solve into a
#: 400-action failure. Measured 2026-11-16.
PAGE_SEARCH = {
    "utterance": 'Use the textbox to enter "Nathalie" and press "Search", then find and click '
                 'the 3rd search result.',
    "elements": [
        {"index": 4, "tag": "input", "type": "text", "value": "", "can_type": True},
        {"index": 5, "tag": "button", "text": "Search", "can_click": True},
        {"index": 6, "tag": "div", "text": "", "can_click": False},
    ],
}


class EvaluatorIsArithmeticAndNothingElse(unittest.TestCase):
    def test_page_expression_with_trailing_equals_is_evaluated(self):
        # The pages print "7 + 0 =": stripping the "=" AFTER the purity check refused every one
        # of them, which was defect one.
        for source, expected in (("7 + 0 =", "7"), ("(3 + 4) * 2 =", "14"), ("12/4", "3"),
                                 ("-3 + 10", "7")):
            value, reason = dv.evaluate_arithmetic(source)
            self.assertEqual(value, expected, f"{source} -> {reason}")

    def test_names_calls_and_attributes_are_refused_not_executed(self):
        # A computed value is executed, so the evaluator must be an allow-list walk. Each of
        # these WOULD run if the guard were removed, which is what makes the test load-bearing.
        for source in ("__import__('os').system('echo hi')", "open('/etc/passwd').read()",
                       "().__class__", "eval('1+1')", "1 if 1 else 2"):
            value, reason = dv.evaluate_arithmetic(source)
            self.assertIsNone(value, source)
            self.assertTrue(reason.startswith(("EVAL_NOT_PURE_ARITHMETIC", "EVAL_REFUSED_")), reason)

    def test_exponent_and_magnitude_are_bounded(self):
        self.assertEqual(dv.evaluate_arithmetic("2 ** 10 ** 9")[0], None)
        self.assertEqual(dv.evaluate_arithmetic("2 ** 3")[0], "8")
        self.assertEqual(dv.evaluate_arithmetic("999999999999 * 999999999999")[0], None)

    def test_division_by_zero_is_a_refusal_not_a_crash(self):
        self.assertEqual(dv.evaluate_arithmetic("1 / 0"), (None, "EVAL_DIVIDED_BY_ZERO"))


class LinearIsGeneralOverSides(unittest.TestCase):
    def test_unknown_on_either_side(self):
        # The corpus put the unknown on the right on half the seeds; a first draft assumed the
        # left and refused those pages. That was defect two.
        for source, expected in (("x + 7 = 5", "-2"), ("8 + x = 33", "25"), ("33 = 8 + x", "25"),
                                 ("7 - x = 2", "5"), ("2x = 9", "4.5"), ("-x + 2 = 5", "-3"),
                                 ("2x + 3 = x + 5", "2")):
            self.assertEqual(dv.solve_linear(source)[0], expected, source)

    def test_non_linear_is_refused_by_name(self):
        for source in ("x*x = 4", "x = y", "sin(x) = 1", "2 = 3"):
            value, reason = dv.solve_linear(source)
            self.assertIsNone(value, source)
            self.assertIn(reason, ("LINEAR_NOT_LINEAR", "LINEAR_NOT_AN_EQUATION",
                                   "LINEAR_NO_VARIABLE"), source)

    def test_integral_answers_are_written_as_integers(self):
        self.assertEqual(dv.format_number(7.0), "7")
        self.assertEqual(dv.format_number(-2.0000000001), "-2")


class ClockIsTwelveHourToTwentyFour(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(dv.clock24("Enter 7:55 PM as the time")[0], "19:55")
        self.assertEqual(dv.clock24("7:55 am")[0], "07:55")
        self.assertEqual(dv.clock24("12:30 AM")[0], "00:30")
        self.assertEqual(dv.clock24("12:30 PM")[0], "12:30")

    def test_no_time_is_a_refusal(self):
        self.assertEqual(dv.clock24("no clock here"), (None, "CLOCK_NO_TIME_FOUND"))


class WhatIsOfferedToType(unittest.TestCase):
    def test_computed_value_is_offered_before_the_bare_page_literal(self):
        values = [row["value"] for row in dv.derivations(PAGE_ARITHMETIC)]
        self.assertIn("7", values)
        self.assertLess(values.index("7"), values.index("7 + 0 ="),
                        "the aimed value must be tried before the text it was computed from")

    def test_a_control_label_is_not_a_value_to_type(self):
        # Defect three: "Search" is what the user presses, not what the user types. Offering it
        # made the search box hold the wrong query and the page unreachable.
        values = [row["value"] for row in dv.derivations(PAGE_SEARCH)]
        self.assertIn("Nathalie", values)
        self.assertNotIn("Search", values)

    def test_the_cap_is_a_cap(self):
        page = {"utterance": "type the text below",
                "elements": [{"index": i, "tag": "span", "text": f"word{i}"} for i in range(40)]
                           + [{"index": 99, "tag": "input", "value": "", "can_type": True}]}
        self.assertLessEqual(len(dv.derivations(page, limit=5)), 5)

    def test_typed_actions_target_only_fields_that_take_text(self):
        actions = dv.typed_actions(PAGE_ALGEBRA)
        self.assertTrue(actions)
        self.assertTrue(all(a.startswith("type@6=") for a in actions), actions)

    def test_rule_of_names_the_rule_that_produced_the_value(self):
        row = dv.rule_of(PAGE_ALGEBRA, "type@6=25")
        self.assertEqual(row["rule"], "LINEAR")
        self.assertIsNone(dv.rule_of(PAGE_ALGEBRA, "type@6=not-a-derived-value"))
        self.assertIsNone(dv.rule_of(PAGE_ALGEBRA, "click@7"))


class AffordanceKeyTransfersAcrossPages(unittest.TestCase):
    def test_the_same_kind_of_control_gets_the_same_key_at_a_different_index(self):
        left = {"elements": [{"index": 0, "tag": "body"},
                             {"index": 1, "tag": "div"},
                             {"index": 2, "tag": "span"},
                             {"index": 3, "tag": "button", "can_click": True},
                             {"index": 4, "tag": "div"}, {"index": 5, "tag": "div"},
                             {"index": 6, "tag": "div"}, {"index": 7, "tag": "div"},
                             {"index": 8, "tag": "div"}, {"index": 9, "tag": "button", "can_click": True}]}
        self.assertEqual(classify(left, "click@3"), classify(left, "click@9"))
        self.assertEqual(classify(left, "click@3"), "click|button|pressable")

    def test_nothing_is_deferred_before_it_has_been_looked_at(self):
        prior = InertActionPrior()
        self.assertFalse(prior.is_deferred(classify(PAGE_SEARCH, "click@5")))
        prior.observe(PAGE_SEARCH, "click@5", changed=True)
        self.assertFalse(prior.is_deferred(classify(PAGE_SEARCH, "click@5")))

    def test_a_class_that_never_changes_is_deferred_and_costs_more_the_more_evidence(self):
        page = {"elements": [{"index": 2, "tag": "div", "can_click": True}]}
        prior = InertActionPrior(min_observations=2)
        prior.observe(page, "hover@2", changed=False)
        self.assertFalse(prior.is_deferred(classify(page, "hover@2")), "one look is not evidence")
        prior.observe(page, "hover@2", changed=False)
        self.assertTrue(prior.is_deferred(classify(page, "hover@2")))
        first = prior.price(page, "hover@2")[0]
        prior.observe(page, "hover@2", changed=False)
        self.assertGreater(prior.price(page, "hover@2")[0], first)
        self.assertLess(first, 10 ** 6, "the price must stay an order, not a wall")

    def test_a_known_good_class_is_never_deferred(self):
        page = {"elements": [{"index": 1, "tag": "input", "type": "text", "can_type": True}]}
        prior = InertActionPrior(min_observations=1)
        for _ in range(20):
            prior.observe(page, "type@1=hello", changed=True)
        self.assertFalse(prior.is_deferred(classify(page, "type@1=hello")))
        self.assertEqual(prior.price(page, "type@1=hello"), (0, 1))

    def test_counts_add_rather_than_average_when_a_prior_moves(self):
        page = {"elements": [{"index": 0, "tag": "div", "can_click": True}]}
        one, other = InertActionPrior(), InertActionPrior()
        one.observe(page, "grab@0", changed=False)
        other.observe(page, "grab@0", changed=False)
        one.absorb(other)
        self.assertEqual(one.table()[classify(page, "grab@0")]["tries"], 2)

    def test_two_different_priors_do_not_share_state(self):
        page = {"elements": [{"index": 0, "tag": "div", "can_click": True}]}
        one = InertActionPrior()
        two = InertActionPrior()
        one.observe(page, "grab@0", changed=False)
        self.assertEqual(two.table(), {})
        self.assertNotEqual(one.digest(), two.digest())


class TheMeasurementArmsDifferOnlyInWhatMayBeTyped(unittest.TestCase):
    def test_pressing_actions_are_identical_in_every_arm(self):
        from canonical.tools import derived_value_measure_v1 as arm_tool

        page = {"utterance": 'enter "Nathalie"', "elements": [
            {"index": 0, "tag": "div", "text": "search", "can_click": True},
            {"index": 1, "tag": "input", "type": "text", "value": "", "can_type": True}]}
        sets = {}
        for arm in ("A_shipped_hand", "E_derived_hand", "U_union", "D_decoy_derived"):
            actions = arm_tool.actions_arm(page, arm)
            sets[arm] = {a for a in actions if not a.startswith("type@")}
            self.assertTrue(any(a.startswith("type@") for a in actions), arm)
        for arm, pressing in sets.items():
            self.assertEqual(pressing, sets["A_shipped_hand"], arm)

    def test_the_decoy_arm_offers_a_literal_value_somewhere_else(self):
        from canonical.tools import derived_value_measure_v1 as arm_tool

        page = {"utterance": 'enter "Nathalie" and press "Search"', "elements": [
            {"index": 1, "tag": "input", "type": "text", "value": "", "can_type": True}]}
        derived = [a for a in arm_tool.actions_arm(page, "E_derived_hand") if a.startswith("type@")]
        decoy = [a for a in arm_tool.actions_arm(page, "D_decoy_derived") if a.startswith("type@")]
        self.assertTrue(decoy, "the control must offer values, or it tests nothing")
        self.assertFalse(set(derived) & set(decoy),
                         "the control must not contain the treatment's values")

    def test_the_holdout_split_is_disjoint_and_reproducible(self):
        from canonical.tools.inert_action_prior_measure_v1 import holdout_split

        tasks = [f"task-{i}" for i in range(20)]
        learn, score = holdout_split(tasks)
        self.assertFalse(set(learn) & set(score))
        self.assertEqual((learn, score), holdout_split(tasks))
        self.assertEqual(sorted(learn + score), sorted(tasks))


class TheReceiptsAgreeWithTheRuns(unittest.TestCase):
    """A committed receipt whose totals do not equal its rows is a claim nobody can check."""

    def test_derived_value_receipt_totals_fold_from_rows(self):
        path = REPO / "canonical/verification/DERIVED_VALUE_20261116_V1.json"
        if not path.is_file():
            self.skipTest("receipt not written yet")
        data = json.loads(path.read_text())
        pages = data["pages"]
        self.assertEqual(data["summary"]["pages"], len(pages))
        for arm, row in data["summary"]["arms"].items():
            self.assertEqual(row["pass"], sum(1 for p in pages if p["arms"][arm]["pass"]), arm)
            self.assertEqual(row["actions_spent"],
                             sum(int(p["arms"][arm]["budget_spent"]) for p in pages), arm)

    def test_inert_prior_receipt_totals_fold_from_rows(self):
        path = REPO / "canonical/verification/INERT_ACTION_PRIOR_20261116_V1.json"
        if not path.is_file():
            self.skipTest("receipt not written yet")
        data = json.loads(path.read_text())
        pages = data["pages"]
        self.assertEqual(data["summary"]["pages"], len(pages))
        for arm, row in data["summary"]["arms"].items():
            self.assertEqual(row["pass"], sum(1 for p in pages if p["arms"][arm]["pass"]), arm)


if __name__ == "__main__":
    unittest.main()
