"""Pin every number the one-try coverage memo quotes.

The tool reads one record and groups it. These tests fail if the record moves under the memo,
if a refusal sentence stops being classified, or if the arithmetic that separates coverage from
precision is changed.
"""
from __future__ import annotations

import unittest

from canonical.tools.one_try_coverage_frontier_20261112_v1 import (
    SCHEMA,
    classify,
    dose,
    frontier,
    load,
    report,
    spread,
)


class DoseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = load()

    def test_current_organ_one_example(self):
        row = dose(self.record, "current_whole_file")["one"]
        self.assertEqual(row["asked"], 440)
        self.assertEqual(row["edited"], 87)
        self.assertEqual(row["developers_changes"], 1674)
        self.assertEqual(row["right"], 265)
        self.assertAlmostEqual(row["coverage"], 0.158303, places=6)
        self.assertEqual(row["organ_changes"], 286)
        self.assertEqual(row["organ_right"], 273)
        self.assertAlmostEqual(row["precision"], 0.954545, places=6)

    def test_current_organ_two_examples(self):
        row = dose(self.record, "current_whole_file")["two"]
        self.assertEqual(row["asked"], 870)
        self.assertEqual(row["edited"], 222)
        self.assertEqual(row["right"], 797)
        self.assertAlmostEqual(row["coverage"], 0.239627, places=6)
        self.assertEqual(row["organ_changes"], 855)
        self.assertEqual(row["organ_right"], 826)
        self.assertAlmostEqual(row["precision"], 0.966082, places=6)

    def test_second_example_buys_about_eight_points(self):
        for key in ("older_organ_whole_file", "current_whole_file",
                    "current_leave_unshown", "ceiling_every_try_kept"):
            marginal = dose(self.record, key)["second_example_buys_coverage"]
            self.assertGreater(marginal, 0.08)
            self.assertLess(marginal, 0.10)
        self.assertAlmostEqual(
            dose(self.record, "current_whole_file")["second_example_buys_coverage"],
            0.081324, places=6)

    def test_ceiling_is_still_a_fraction(self):
        one = dose(self.record, "ceiling_every_try_kept")["one"]
        two = dose(self.record, "ceiling_every_try_kept")["two"]
        self.assertAlmostEqual(one["coverage"], 0.232975, places=6)
        self.assertAlmostEqual(one["precision"], 0.96837, places=6)
        self.assertAlmostEqual(two["coverage"], 0.321708, places=6)
        self.assertAlmostEqual(two["precision"], 0.974291, places=6)

    def test_coverage_and_precision_are_not_the_same_fraction(self):
        row = dose(self.record, "current_whole_file")["one"]
        self.assertLess(row["coverage"], 0.20)
        self.assertGreater(row["precision"], 0.95)


class SpreadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = load()

    def test_one_example_recovers_nothing_on_five_of_fifteen(self):
        row = spread(self.record)
        self.assertEqual(row["pull_requests"], 15)
        self.assertEqual(row["zero"], 5)
        self.assertEqual(row["at_most_one_percent"], 6)
        self.assertAlmostEqual(row["median"], 0.090909, places=6)
        self.assertAlmostEqual(row["best"], 0.588235, places=6)


class FrontierTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = load()
        cls.row = frontier(cls.record)

    def test_every_asking_is_classified(self):
        self.assertEqual(sum(self.row["counts"].values()), self.row["asked"])
        self.assertNotIn("OTHER", self.row["counts"])

    def test_counts(self):
        counts = self.row["counts"]
        self.assertEqual(counts["NO_FORM_IN_FILE"], 162)
        self.assertEqual(counts["EDITED"], 87)
        self.assertEqual(counts["IMPORT_ONLY_EXAMPLE"], 60)
        self.assertEqual(counts["CALL_SHAPE_NOT_SHOWN"], 50)
        self.assertEqual(counts["BLOCK_SHAPE"], 34)
        self.assertEqual(counts["NAME_NOT_AVAILABLE"], 22)
        self.assertEqual(counts["CONFLICTING_CONTEXT"], 15)
        self.assertEqual(counts["PARSE_MISMATCH"], 10)

    def test_ordinary_refusals_are_the_operator_frontier(self):
        self.assertEqual(self.row["operator_gap_askings"], 191)
        self.assertAlmostEqual(self.row["operator_gap_share"], 0.434091, places=6)
        ranked = [row["class"] for row in self.row["ranked_operator_gaps"]]
        self.assertEqual(ranked[0], "IMPORT_ONLY_EXAMPLE")
        self.assertEqual(ranked[1], "CALL_SHAPE_NOT_SHOWN")
        self.assertEqual(ranked[2], "BLOCK_SHAPE")
        self.assertNotIn("NO_FORM_IN_FILE", ranked)
        self.assertNotIn("EDITED", ranked)

    def test_a_truncated_call_shape_sentence_is_still_classified(self):
        self.assertEqual(
            classify("refused: line N of the file has logger.warn called with N arguments"),
            "CALL_SHAPE_NOT_SHOWN",
        )


class ReportTest(unittest.TestCase):
    def test_schema_record_and_limits(self):
        rep = report()
        self.assertEqual(rep["schema"], SCHEMA)
        self.assertEqual(rep["record"],
                         "canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json")
        self.assertEqual(rep["generated_utc"], "2026-11-12T17:19:18Z")
        self.assertTrue(any("not a new run" in line for line in rep["limits"]))
        self.assertTrue(any("askings, not changes" in line for line in rep["limits"]))


if __name__ == "__main__":
    unittest.main()
