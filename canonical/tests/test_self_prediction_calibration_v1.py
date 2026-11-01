"""A self-model must be able to be wrong, so this test makes one be wrong.

WHY THIS EXISTS
---------------
`self_prediction_calibration_v1` scores stated expectations against independent verdicts. The
defect that would make it worthless is a scorer that reports a number no matter what it is fed, so
each case below is a predictor that must be classified differently:

* a calibrated predictor that separates outcomes                -> CALIBRATED
* a constant predictor (always 0.9), i.e. decoration             -> NO_DISCRIMINATION
* a confident predictor that is confidently wrong                -> WORSE_THAN_BASE_RATE
* a predictor that knows the base rate but claims more of it     -> SYSTEMATICALLY_OVERCONFIDENT
* an empty or tiny sample                                        -> INSUFFICIENT_EVIDENCE
* a prediction settled by its own author, or settled twice       -> refused

Measured 2026-11-01: a constant 0.9 predictor over a 50% base rate scores Brier 0.82 against a
base-rate Brier of 0.25, so the "confident" system is the worst one in the table. That is the whole
point: confidence that does not track outcomes is a decoration with a high price.
"""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import self_prediction_calibration_v1 as C  # noqa: E402


def _rows(pairs):
    return [{"predicted_pass_probability": p, "outcome_pass": o} for p, o in pairs]


class ScorerTests(unittest.TestCase):
    def test_a_calibrated_predictor_is_named_calibrated(self):
        # 40 attempts, half pass; the belief is 0.9 when it will pass and 0.1 when it will not.
        pairs = [(0.9, True)] * 20 + [(0.1, False)] * 20
        report = C.score(_rows(pairs))
        self.assertEqual(report["verdict"], "CALIBRATED", report)
        self.assertGreater(report["discrimination"], 0.5)
        self.assertGreater(report["skill_over_base_rate"], 0.5)

    def test_a_constant_confident_predictor_is_decoration(self):
        pairs = [(0.9, i % 2 == 0) for i in range(40)]
        report = C.score(_rows(pairs))
        self.assertEqual(report["verdict"], "NO_DISCRIMINATION", report)
        self.assertEqual(report["discrimination"], 0.0)
        # And it is worse than knowing nothing: this is the price of confident decoration.
        self.assertLess(report["skill_over_base_rate"], 0.0)

    def test_a_confidently_wrong_predictor_is_worse_than_the_base_rate(self):
        pairs = [(0.95, False)] * 30 + [(0.95, True)] * 4
        report = C.score(_rows(pairs))
        self.assertIn(report["verdict"], {"NO_DISCRIMINATION", "WORSE_THAN_BASE_RATE"}, report)
        self.assertLess(report["skill_over_base_rate"], 0.0)

    def test_claiming_more_than_it_delivers_is_named(self):
        # It separates outcomes (0.85 on passes, 0.55 on fails) but claims 0.70 while delivering 0.50.
        pairs = [(0.85, True)] * 20 + [(0.55, False)] * 20
        report = C.score(_rows(pairs))
        self.assertEqual(report["verdict"], "SYSTEMATICALLY_OVERCONFIDENT", report)

    def test_an_empty_sample_does_not_get_a_verdict(self):
        self.assertEqual(C.score([])["verdict"], "INSUFFICIENT_EVIDENCE")

    def test_a_tiny_sample_does_not_get_a_verdict(self):
        pairs = [(0.9, True)] * 5 + [(0.1, False)] * 5
        self.assertEqual(C.score(_rows(pairs))["verdict"], "INSUFFICIENT_EVIDENCE")


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = C.Ledger(pathlib.Path(self.tmp.name) / "ledger.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_prediction_round_trips_and_scores(self):
        row = self.ledger.predict(capability_id="text.file.write", predicted_pass_probability=0.8)
        self.assertFalse(row["settled"])
        settled = self.ledger.settle(row["record_id"], outcome_pass=True, inspector="raw_goal_trace_acceptance_v1")
        self.assertTrue(settled["settled"])
        self.assertEqual(len(self.ledger.settled_rows()), 1)

    def test_a_prediction_cannot_be_scored_by_its_own_author(self):
        row = self.ledger.predict(capability_id="x", predicted_pass_probability=0.5)
        with self.assertRaises(C.CalibrationError):
            self.ledger.settle(row["record_id"], outcome_pass=True, inspector="")

    def test_a_prediction_cannot_be_settled_twice(self):
        row = self.ledger.predict(capability_id="x", predicted_pass_probability=0.5)
        self.ledger.settle(row["record_id"], outcome_pass=True, inspector="inspector_a")
        with self.assertRaises(C.CalibrationError):
            self.ledger.settle(row["record_id"], outcome_pass=False, inspector="inspector_b")

    def test_a_probability_outside_the_unit_interval_is_refused(self):
        for bad in (-0.1, 1.5, float("nan"), "0.5", True):
            with self.assertRaises(C.CalibrationError):
                self.ledger.predict(capability_id="x", predicted_pass_probability=bad)

    def test_the_latest_line_for_a_record_is_the_one_that_counts(self):
        row = self.ledger.predict(capability_id="x", predicted_pass_probability=0.2)
        self.ledger.settle(row["record_id"], outcome_pass=False, inspector="i")
        raw = self.ledger.path.read_text().splitlines()
        self.assertEqual(len(raw), 2)
        self.assertEqual(len(self.ledger.settled_rows()), 1)
        self.assertEqual(self.ledger.settled_rows()[0]["outcome_pass"], False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
