"""Pin the three facts that decide the route through Problem 2.

The memo this guards (`WHICH_FIX_ACTUALLY_WORKS_20261112_V1.md`) makes three claims, and each one
is a claim that a reader could check and find false later, so each one is pinned here:

1. The recorded roadmap's "askings" per refusal class are not independent opportunities. They are
   examples times the other files in the same pull request, so a class whose *example* cannot be
   read at all is counted as many askings and offers zero of them to an apply-time operator.
2. Naming a missing name is not free. It buys the largest strict-coverage gain of any single
   operator and costs real precision, because the target file really did not have the name.
3. A rename that leaves the arguments alone buys both metrics and adds no wrong change.

The numbers come from the recorded run, so these tests fail if the organ, the corpus protocol, or
the arithmetic moves.
"""
from __future__ import annotations

import unittest

from canonical.tools.which_fix_moves_generalization_v1 import CLASSES, classify


class ClassifyTest(unittest.TestCase):
    def test_every_roadmap_class_is_recognised_from_the_organs_own_words(self):
        for name, spec in CLASSES.items():
            self.assertEqual(classify("refused: " + spec["match"] + " at line 3"), name,
                             "%s no longer matches the organ's sentence" % name)

    def test_an_edit_is_not_a_refusal(self):
        self.assertEqual(classify(None), "EDITED")

    def test_an_unrecognised_refusal_is_other_not_a_class(self):
        self.assertEqual(classify("refused: something the organ has never said"), "OTHER")

    def test_no_form_in_file_is_marked_as_not_a_fix(self):
        self.assertIn("NOT A FIX", CLASSES["NO_FORM_IN_FILE"]["real_price"])

    def test_the_cheap_class_says_its_real_price(self):
        for name, spec in CLASSES.items():
            self.assertTrue(spec["real_price"].strip(), name)
            self.assertFalse(spec["real_price"].lower().startswith("none"), name)


class RecordedFindingTest(unittest.TestCase):
    """The numbers in the memo, read from the record the tool wrote."""

    @classmethod
    def setUpClass(cls):
        from canonical.tools.which_fix_moves_generalization_v1 import ROOT
        import json
        path = ROOT / "canonical/verification/WHICH_FIX_MOVES_GENERALIZATION_20261112_V1.json"
        cls.record = json.loads(path.read_text(encoding="utf-8"))

    def test_the_record_names_the_organ_it_was_measured_on(self):
        """Pin the organ this record belongs to, so a later change to it cannot leave the numbers stale.

        Before this turn the organ was `0cca78be` and this record was made with the kept-name
        exemption switched off. It is now `ada1c5ed` with the exemption in, and that is why the
        `call_shape` arm is no longer a ceiling but the behaviour of `main`.
        """
        self.assertEqual(
            self.record["code_sha256"]["canonical/swe_kernel/taught_actions/edit_by_example_v1.py"],
            "ada1c5ed3422eee55d2e2ea65bb8afe56cdc1613895726499335cd32bdb7e0f0")

    def test_the_published_baseline_is_reproduced(self):
        base = self.record["baseline"]
        self.assertEqual(base["askings"], 440)
        self.assertEqual(base["classes"]["NO_FORM_IN_FILE"], 168)
        self.assertEqual(base["classes"]["IMPORT_ONLY_EXAMPLE"], 60)
        # The class table runs on the shipped organ, so its baseline is the post-fix precision,
        # not the 0.9241 the pre-fix organ scored. The pre-fix figure is the `baseline` ARM below.
        self.assertEqual(round(base["strict_precision"], 4), 0.9461)

    def test_the_three_read_time_classes_offer_zero_reachable_askings(self):
        """This is the finding that reorders the roadmap: these are not operator problems."""
        for name in ("IMPORT_ONLY_EXAMPLE", "BLOCK_SHAPE", "CONFLICTING_CONTEXT"):
            row = self.record["classes"][name]
            self.assertEqual(row["askings_left_that_an_operator_could_reach"], 0, name)
            self.assertEqual(row["askings_where_the_example_itself_cannot_be_read"],
                             row["askings_of_this_class"], name)

    def test_name_availability_is_still_the_one_reachable_apply_time_class(self):
        """The rename class is gone from this table because the shipped organ no longer refuses it."""
        row = self.record["classes"]["NAME_NOT_AVAILABLE"]
        self.assertEqual(row["askings_left_that_an_operator_could_reach"],
                         row["askings_of_this_class"])
        self.assertEqual(row["askings_where_the_example_itself_cannot_be_read"], 0)
        self.assertNotIn("CALL_SHAPE_NOT_SHOWN", self.record["classes"])

    def test_the_fifty_rename_askings_became_edits_and_nothing_else(self):
        """The consistency check that makes the gain attributable: 90 + 50 = 140, and no new wrong change."""
        classes = self.record["baseline"]["classes"]
        self.assertEqual(classes["EDITED"], 140)
        self.assertEqual(classes["NO_FORM_IN_FILE"], 168)

    def test_the_rank_is_by_measured_gain_not_by_asking_count(self):
        order = self.record["ranked_by_measured_gain"]
        self.assertEqual(order[0], "NAME_NOT_AVAILABLE")
        self.assertLess(order.index("BLOCK_SHAPE"), order.index("IMPORT_ONLY_EXAMPLE"))

    def test_the_biggest_gain_is_not_the_biggest_class(self):
        """60 askings buy nothing; 22 buy the most. That inversion is the memo."""
        self.assertEqual(self.record["classes"]["IMPORT_ONLY_EXAMPLE"]["strict_coverage_gain_pp"], 0.0)
        self.assertGreater(self.record["classes"]["NAME_NOT_AVAILABLE"]["strict_coverage_gain_pp"], 0)

    def test_the_rename_arm_buys_both_metrics_and_no_wrong_change(self):
        """This arm is now REALIZED in the organ, not a ceiling: it is what `main` does."""
        arms = self.record["arms"]
        self.assertEqual(arms["call_shape"]["not_what_the_developers_did"],
                         arms["baseline"]["not_what_the_developers_did"],
                         "a pure rename must not add a wrong change")
        self.assertGreater(arms["call_shape"]["strict_coverage"], arms["baseline"]["strict_coverage"])
        self.assertGreater(arms["call_shape"]["marker_same_share"], arms["baseline"]["marker_same_share"])
        self.assertGreater(arms["call_shape"]["strict_precision"], arms["baseline"]["strict_precision"])

    def test_the_shipped_gain_is_these_exact_numbers(self):
        arms = self.record["arms"]
        self.assertEqual(arms["baseline"]["strict_coverage"], 0.2082)
        self.assertEqual(arms["call_shape"]["strict_coverage"], 0.2999)
        self.assertEqual(arms["call_shape"]["strict_precision"], 0.9461)
        self.assertEqual(arms["call_shape"]["marker_same_share"], 0.617)

    def test_naming_a_name_buys_recall_by_spending_precision(self):
        """The trap in the memo: the biggest coverage gain also breaks the most files."""
        arms = self.record["arms"]
        self.assertLess(arms["extend_import"]["strict_precision"],
                        arms["call_shape"]["strict_precision"])
        self.assertGreater(arms["extend_import"]["not_what_the_developers_did"],
                           arms["call_shape"]["not_what_the_developers_did"])
        self.assertLess(arms["extend_import"]["marker_same_share"],
                        arms["baseline"]["marker_same_share"])

    def test_the_two_scorers_disagree_in_sign_for_naming_a_name(self):
        """Strict coverage up, marker share down to zero. Quoting one alone would be a lie."""
        row = self.record["classes"]["NAME_NOT_AVAILABLE"]
        self.assertGreater(row["strict_coverage_gain_pp"], 0)
        self.assertEqual(row["corpus_marker_same_if_lifted"], self.record["baseline"]["marker_same_share"])

    def test_no_model_was_called(self):
        self.assertEqual(self.record["model_calls"], 0)
        self.assertEqual(self.record["incremental_spend_usd"], 0)
        self.assertFalse(self.record["terminal_authority"])


if __name__ == "__main__":
    unittest.main()
