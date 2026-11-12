#!/usr/bin/env python3
"""What the "when should one showing be trusted" record must keep saying.

Every number here is read from the record this round wrote, or from the recorded corpus it was
measured on. The tests exist so that a later change to the organ, the corpus, or the tool cannot
quietly move a figure the write-up quotes.

Two of these tests are about mistakes this round actually made and must not repeat:

  * the abstention claim was first written as ``cost >= 0``, comparing a precision against a count,
    so it "held" without testing anything (``test_the_abstention_claim_compares_like_with_like``);
  * the import-line share was first read from an aggregate row that does not carry it, which raised
    a KeyError instead of reporting a number
    (``test_the_import_share_is_summed_from_the_finer_grain``).
"""
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
RECORD = ROOT / "canonical/verification/WHEN_ONE_SHOWING_SHOULD_BE_TRUSTED_20261112_V1.json"
CORPUS_RECORD = ROOT / "canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json"


def summary() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))["summary"]


class TheRecordExists(unittest.TestCase):
    def test_the_record_is_present_and_declares_no_authority(self):
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        self.assertEqual(record["schema"], "WHEN_ONE_SHOWING_SHOULD_BE_TRUSTED_V1")
        self.assertIn("NONE", record["authority"])
        self.assertFalse(record["truth_achieved"])
        self.assertFalse(record["terminal_authority"])
        self.assertEqual(record["model_calls"], 0)
        self.assertEqual(record["incremental_spend_usd"], 0)

    def test_the_corpus_is_the_recorded_one_and_not_re_selected(self):
        """The measurement must be like-for-like with the recorded run: same 15 pull requests."""
        measured = json.loads(RECORD.read_text(encoding="utf-8"))
        recorded = json.loads(CORPUS_RECORD.read_text(encoding="utf-8"))
        self.assertEqual(len(measured["tasks"]), len(recorded["pull_requests"]))
        self.assertEqual({t["name"] for t in measured["tasks"]},
                         {p["name"] for p in recorded["pull_requests"]})


class ThePriceOfAChoice(unittest.TestCase):
    def test_the_chosen_demonstrations_precision_is_not_the_pooled_precision(self):
        """The headline correction: 95.45% is per asking; the decision sees 87.0%."""
        headline = summary()["headline"]
        self.assertAlmostEqual(headline["precision_of_the_chosen_demonstration"], 0.8696, places=3)
        self.assertAlmostEqual(headline["recorded_pooled_precision_for_comparison"], 0.9545, places=4)
        self.assertLess(headline["precision_of_the_chosen_demonstration"],
                        headline["recorded_pooled_precision_for_comparison"])

    def test_choosing_by_reach_now_captures_67_percent_of_the_best(self):
        """The recorded round reported 0.86 against a spread of candidate SHARES.

        Against the ceiling on the absolute number of changes recoverable -- a different
        denominator -- the same choice rule captures 80 of 119. Both are true; the record states
        which is which so neither can be quoted as the other.
        """
        headline = summary()["headline"]
        self.assertEqual(headline["changes_recovered_choosing_by_reach"], 80)
        self.assertEqual(headline["changes_recovered_choosing_the_best"], 119)
        self.assertAlmostEqual(headline["share_of_best_captured"], 80 / 119, places=4)


class Calibration(unittest.TestCase):
    def test_precision_by_reach_is_pinned(self):
        table = {row["reach"]: row for row in summary()["precision_by_reach"]}
        self.assertEqual(table[1]["right"], 24)
        self.assertEqual(table[1]["wrong"], 2)
        self.assertEqual(table[2]["right"], 122)
        self.assertEqual(table[2]["wrong"], 2)
        self.assertEqual(table[3]["wrong"], 0)
        self.assertEqual(table[3]["precision"], 1.0)
        self.assertEqual(table[4]["wrong"], 10)
        self.assertEqual(table[5]["wrong"], 0)
        self.assertEqual(table[5]["precision"], 1.0)

    def test_reach_is_not_monotone_in_precision(self):
        """Ten of the twelve wrong changes sit at reach 4, above the exact stratum at reach 3."""
        table = {row["reach"]: row for row in summary()["precision_by_reach"]}
        self.assertGreater(table[4]["wrong"], table[2]["wrong"])
        self.assertLess(table[4]["precision"], table[3]["precision"])

    def test_reach_zero_never_edits_anything(self):
        """A demonstration whose lesson fits no sibling must not produce a change anywhere."""
        table = {row["reach"]: row for row in summary()["precision_by_reach"]}
        self.assertEqual(table[0]["organ_changes"], 0)


class Abstention(unittest.TestCase):
    def test_abstaining_at_one_declines_four_tasks_for_free(self):
        policies = {row["minimum_reach"]: row for row in summary()["abstention_policies"]}
        self.assertEqual(policies[1]["tasks_declined"], 4)
        self.assertEqual(policies[1]["tasks_acted_on"], 11)
        self.assertEqual(policies[1]["changes_right"], policies[0]["changes_right"])

    def test_the_abstention_claim_compares_like_with_like(self):
        """The defect this round made: 0.8696 >= 0 'held' without measuring anything.

        The claim is now an equality of two counts, and both counts must be present.
        """
        claim = summary()["pre_registered_prediction"]["claims"]["declining_at_reach_ge_1_costs_nothing"]
        for key in ("changes_right_at_threshold_0", "changes_right_at_threshold_1",
                    "changes_wrong_at_threshold_0", "changes_wrong_at_threshold_1", "tasks_declined"):
            self.assertIn(key, claim, f"the claim must carry {key} to be checkable")
        self.assertIsInstance(claim["held"], bool)
        self.assertEqual(claim["held"],
                         claim["changes_right_at_threshold_0"] == claim["changes_right_at_threshold_1"]
                         and claim["changes_wrong_at_threshold_0"] == claim["changes_wrong_at_threshold_1"])

    def test_abstention_buys_no_precision(self):
        """Declining is free, and that is all it is: the twelve wrong changes stay wrong."""
        policies = {row["minimum_reach"]: row for row in summary()["abstention_policies"]}
        self.assertEqual(policies[1]["changes_wrong"], policies[0]["changes_wrong"])
        self.assertGreater(policies[1]["changes_wrong"], 0)

    def test_the_only_perfect_operating_point_declines_thirteen_of_fifteen(self):
        policies = {row["minimum_reach"]: row for row in summary()["abstention_policies"]}
        self.assertEqual(policies[5]["precision_of_the_decision"], 1.0)
        self.assertEqual(policies[5]["changes_wrong"], 0)
        self.assertEqual(policies[5]["tasks_declined"], 13)
        self.assertEqual(policies[5]["tasks_acted_on"], 2)

    def test_every_policy_is_reported_so_the_threshold_cannot_be_chosen_after_the_fact(self):
        policies = summary()["abstention_policies"]
        self.assertEqual([row["minimum_reach"] for row in policies], [0, 1, 2, 3, 4, 5])


class TheInvisibleClass(unittest.TestCase):
    def test_the_import_share_is_summed_from_the_finer_grain(self):
        """The aggregate row does not carry ``developers_changes``; reading it raised KeyError."""
        recorded = json.loads(CORPUS_RECORD.read_text(encoding="utf-8"))
        run = recorded["the_runs"]["2_the_organ_as_main_has_it_now__the_whole_file_or_nothing"]
        self.assertNotIn("developers_changes", run["one_example"])

    def test_215_of_the_1889_changes_are_import_lines(self):
        share = summary()["import_line_changes_the_metric_excludes"]
        self.assertEqual(share["changes_including_import_lines"], 1889)
        self.assertEqual(share["changes_excluding_import_lines"], 1674)
        self.assertEqual(share["import_line_changes"], 215)
        self.assertAlmostEqual(share["share_of_changes_that_are_import_lines"], 0.1138, places=3)


class ThePredictionsWereRegistered(unittest.TestCase):
    def test_all_three_claims_are_scored_and_carried(self):
        claims = summary()["pre_registered_prediction"]["claims"]
        self.assertEqual(len(claims), 3)
        for name, claim in claims.items():
            self.assertIn("held", claim, f"{name} must be scored")
            self.assertIsInstance(claim["held"], bool)

    def test_the_claim_names_match_the_docstring(self):
        """A claim may be restated in the code, but not renamed to something easier to hold."""
        claims = summary()["pre_registered_prediction"]["claims"]
        self.assertEqual(set(claims), {"chosen_precision_below_pooled_95_45",
                                       "reach_not_monotone_in_precision",
                                       "declining_at_reach_ge_1_costs_nothing"})


if __name__ == "__main__":
    unittest.main()


class TheHeldOutCorpusDidNotConfirmTheCurve(unittest.TestCase):
    """The claim the discovery corpus could not test, and the answer it got.

    Six kinds of change the organ had never been run on, from a corpus disjoint by query from the
    fifteen the curve was fitted on. The curve did not hold, and the reason is the finding.
    """

    HELD_OUT = ROOT / "canonical/verification/ONE_SHOWING_HELD_OUT_20261112_V1.json"

    def test_the_corpus_is_disjoint_from_the_discovery_one(self):
        from canonical.tools.hold_out_the_precision_curve_20261112_v1 import overlaps_discovery
        check = overlaps_discovery()
        self.assertTrue(check["disjoint"])
        self.assertEqual(check["collisions"], [])

    def test_on_unseen_kinds_of_change_every_change_the_organ_made_was_wrong(self):
        record = json.loads(self.HELD_OUT.read_text(encoding="utf-8"))
        summary = record["summary"]
        made = sum(row["organ_changes"] for row in summary["precision_by_reach"])
        right = sum(row["right"] for row in summary["precision_by_reach"])
        wrong = sum(row["wrong"] for row in summary["precision_by_reach"])
        self.assertEqual(made, 5)
        self.assertEqual(right, 0)
        self.assertEqual(wrong, 5)

    def test_the_organ_refused_most_of_the_unfamiliar_corpus(self):
        """73.6% of demonstrations unlearnable, against 24.7% on the corpus it was fitted to."""
        record = json.loads(self.HELD_OUT.read_text(encoding="utf-8"))
        summary = record["summary"]
        share = summary["unlearnable_demonstrations"] / summary["candidate_demonstrations"]
        self.assertAlmostEqual(share, 39 / 53, places=4)
        self.assertGreater(share, 0.70)

    def test_the_monotonicity_prediction_failed_and_is_recorded_as_failed(self):
        """A prediction that cannot fail is not a prediction. This one did fail, and stays failed."""
        record = json.loads(self.HELD_OUT.read_text(encoding="utf-8"))
        claims = record["summary"]["pre_registered_prediction"]["claims"]
        self.assertFalse(claims["reach_not_monotone_in_precision"]["held"])
        self.assertFalse(record["summary"]["pre_registered_prediction"]["all_held"])

    def test_the_lower_precision_prediction_did_hold_on_new_kinds(self):
        record = json.loads(self.HELD_OUT.read_text(encoding="utf-8"))
        claim = record["summary"]["pre_registered_prediction"]["claims"]["chosen_precision_below_pooled_95_45"]
        self.assertTrue(claim["held"])
        self.assertEqual(claim["value"], 0.0)
