"""Pin the pair-selection result and the rule that makes it legitimate.

Two kinds of test. The synthetic ones show the mechanism: a pair that has never seen a
three-argument call is refused on a three-argument target, and adding one example that has seen
it makes the same rule apply. The record test pins the fifteen-pull-request result, and proves
that the selector reads no outcome key.
"""
from __future__ import annotations

import json
import pathlib
import unittest

from canonical.tools.demonstration_pair_selection_20261112_v1 import (
    SCHEMA,
    aggregate,
    choose,
    pair_row,
)

RECORD = pathlib.Path("canonical/tests/fixtures/demonstration_pair_selection_summary_v1.json")


def _files():
    """Two two-argument examples, one three-argument example, one three-argument target.

    Use an unlisted rename: ``assertEquals`` -> ``assertEqual`` is a documented alias,
    so the shipped learner correctly allows a different call shape for that specific pair.
    This synthetic case pins the general rule for renames that are not known aliases.
    """
    def pair(name, args):
        names = ", ".join(args)
        return {
            "path": name + ".py",
            "before": "def %s(%s):\n    return check.assertOld(%s)\n" % (name, names, names),
            "after": "def %s(%s):\n    return check.assertNew(%s)\n" % (name, names, names),
        }
    return [pair("a1", ("a", "b")), pair("b1", ("c", "d")),
            pair("c1", ("x", "y", "z")), pair("d1", ("p", "q", "r"))]


class MechanismTest(unittest.TestCase):
    def test_a_pair_that_never_saw_three_arguments_is_refused(self):
        row = pair_row(_files(), 0, 1)
        self.assertTrue(row["learnable"])
        self.assertEqual(row["pred"], 0)
        self.assertEqual(row["pred_files"], 0)
        self.assertEqual(row["right_not_imports"], 0)
        self.assertEqual(row["coverage"], 0.0)

    def test_one_example_with_the_third_argument_makes_the_rule_apply(self):
        row = pair_row(_files(), 0, 2)
        self.assertEqual(row["pred"], 2)
        self.assertEqual(row["pred_files"], 2)
        self.assertEqual(row["right_not_imports"], 2)
        self.assertEqual(row["coverage"], 1.0)

    def test_choose_picks_the_pair_that_applies(self):
        rows = [pair_row(_files(), a, b) for a, b in ((0, 1), (0, 2), (0, 3), (1, 2))]
        self.assertEqual(choose(rows)["pair"], [0, 2])


class OutcomeBlindTest(unittest.TestCase):
    def test_choose_ignores_coverage_and_right(self):
        # The higher-coverage pair has the larger indices; a selector that peeked would take it.
        rows = [
            {"pair": [0, 2], "pred": 3, "pred_files": 2, "coverage": 0.0, "right": 0},
            {"pair": [1, 2], "pred": 3, "pred_files": 2, "coverage": 1.0, "right": 99},
        ]
        self.assertEqual(choose(rows)["pair"], [0, 2])

    def test_choose_prefers_more_files_before_lower_indices(self):
        rows = [
            {"pair": [0, 1], "pred": 5, "pred_files": 1,
             "coverage": 0.0, "right": 0},
            {"pair": [2, 3], "pred": 5, "pred_files": 2,
             "coverage": 0.0, "right": 0},
        ]
        self.assertEqual(choose(rows)["pair"], [2, 3])


class RecordTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text(encoding="utf-8"))
        cls.summary = cls.record["summary"]

    def test_schema_and_corpus(self):
        self.assertEqual(self.record["schema"], SCHEMA)
        self.assertEqual(self.summary["pull_requests"], 15)
        self.assertEqual(self.summary["pairs"], 220)
        self.assertEqual(self.record["baseline_two_example_coverage"], 0.2396)
        self.assertEqual(len(self.record["organ_sha256"]), 64)
        self.assertEqual(len(self.record["corpus_sha256"]), 64)

    def test_pooled_coverages(self):
        for name, coverage in (("all_pairs", 0.231209), ("path", 0.183486),
                               ("largest", 0.19774), ("chosen", 0.617778),
                               ("best", 0.637209)):
            self.assertAlmostEqual(self.summary[name]["coverage"], coverage, places=6)

    def test_precision_is_not_claimed_to_rise(self):
        self.assertAlmostEqual(self.summary["all_pairs"]["precision"], 0.928744, places=6)
        self.assertAlmostEqual(self.summary["chosen"]["precision"], 0.874214, places=6)
        self.assertLess(self.summary["chosen"]["precision"],
                        self.summary["all_pairs"]["precision"])

    def test_the_selection_is_the_result(self):
        self.assertEqual(self.summary["chosen_is_oracle_best"], 12)
        self.assertAlmostEqual(self.summary["chosen_over_all_pairs"], 2.6719, places=4)
        self.assertAlmostEqual(self.summary["chosen_over_oracle"], 0.9695, places=4)
        self.assertAlmostEqual(self.summary["mean_coverage_per_pull_request"]["all_pairs"],
                               0.257603, places=6)
        self.assertAlmostEqual(self.summary["mean_coverage_per_pull_request"]["chosen"],
                               0.497907, places=6)
        self.assertAlmostEqual(self.summary["mean_coverage_per_pull_request"]["best"],
                               0.549418, places=6)

    def test_the_rows_recompute_the_summary(self):
        recomputed = aggregate(self.record["per_pull_request"])
        for name in ("all_pairs", "path", "largest", "chosen", "best"):
            self.assertAlmostEqual(recomputed[name]["coverage"],
                                   self.summary[name]["coverage"], places=6)
        self.assertEqual(recomputed["chosen_is_oracle_best"],
                         self.summary["chosen_is_oracle_best"])

    def test_limits_name_the_two_things_that_could_be_overclaimed(self):
        limits = " ".join(self.record["limits"])
        self.assertIn("agreement with the developers, not correctness", limits)
        self.assertIn("algebra gap, not a selection failure", limits)
        self.assertIn("before-text only", limits)


if __name__ == "__main__":
    unittest.main()
