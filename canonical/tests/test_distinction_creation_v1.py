"""Creating the distinction, tested against the case that refused it.

`witness_inversion_v1` measured why selection cannot do this: 18 real witnesses,
0 expressible as a choice among existing values, because the answer is NEW
content. This module creates a condition instead of selecting one, and every test
here is about the difference between fitting the examples and being sound.
"""
from __future__ import annotations

import unittest

from canonical.swe_kernel import distinction_creation_v1 as dc


class GuardCreationTests(unittest.TestCase):
    def test_a_range_is_created_from_two_sets(self):
        """0..255 is the boundary of a byte, and it is derived, not declared."""
        positives = [{"n": v} for v in (0, 100, 255)]
        negatives = [{"n": v} for v in (256, 300, -1)]
        out = dc.synthesise_guard(positives, negatives)
        self.assertEqual("PASS__GUARD_SYNTHESISED", out["status"])
        self.assertEqual("n between 0 and 255", out["guard"]["render"])
        self.assertEqual(3, out["holds_on_positives"])
        self.assertEqual(3, out["rejects_negatives"])

    def test_a_one_sided_threshold_is_created_when_only_one_edge_is_closed(self):
        """Negatives only below decides the lower edge and NOTHING else.

        A range here would reject 11, which the underlying rule accepts. Earlier
        versions of this module offered `between 1 and 10` and were wrong; the
        sound answer is the one-sided threshold, and it is the one that matches
        what a human writes.
        """
        positives = [{"n": v} for v in (1, 2, 5, 10)]
        negatives = [{"n": v} for v in (0, -1, -5)]
        out = dc.synthesise_guard(positives, negatives)
        self.assertEqual("PASS__GUARD_SYNTHESISED", out["status"])
        self.assertEqual("n gt 0", out["guard"]["render"])
        # and 11 is still accepted, which a range would have refused
        guard = dc.Guard([("n", "gt", 0)])
        self.assertTrue(guard.holds({"n": 11}))

    def test_nested_values_are_flattened_into_features(self):
        positives = [{"order": {"qty": 5}}]
        negatives = [{"order": {"qty": 0}}]
        out = dc.synthesise_guard(positives, negatives)
        self.assertEqual("PASS__GUARD_SYNTHESISED", out["status"])
        self.assertIn("order.qty", out["guard"]["render"])

    def test_a_conjunction_is_created_when_one_atom_cannot_separate(self):
        positives = [{"f": {"n": 5, "d": 2}}]
        negatives = [{"f": {"n": 5, "d": 0}}]
        out = dc.synthesise_guard(positives, negatives)
        self.assertEqual("PASS__GUARD_SYNTHESISED", out["status"])
        self.assertEqual("f.d", out["guard"]["atoms"][0]["feature"].split(".")[0] + "." + out["guard"]["atoms"][0]["feature"].split(".")[1])

    def test_a_string_distinction_is_created(self):
        positives = [{"specifier": ">=1"}, {"specifier": "==1.0"}, {"specifier": "<2"}]
        negatives = [{"specifier": "not-a-spec"}]
        out = dc.synthesise_guard(positives, negatives)
        self.assertEqual("PASS__GUARD_SYNTHESISED", out["status"])
        self.assertFalse(dc.Guard([("specifier", "eq", "not-a-spec")]).holds({"specifier": ">=1"}))


class RefusalsTests(unittest.TestCase):
    def test_one_polarity_cannot_be_separated_from_anything(self):
        out = dc.synthesise_guard([{"x": 1}], [])
        self.assertEqual("REFUSED__NEEDS_BOTH_POLARITIES", out["status"])
        self.assertIsNone(out["guard"])

    def test_the_same_point_labelled_twice_is_refused(self):
        out = dc.synthesise_guard([{"x": 1, "y": 2}], [{"x": 1, "y": 2}])
        self.assertEqual("REFUSED__CONTRADICTORY_EXAMPLES", out["status"])

    def test_no_scalar_features_is_refused(self):
        out = dc.synthesise_guard([{"x": [1, 2]}], [{"x": [3]}])
        self.assertEqual("REFUSED__NO_FEATURES", out["status"])


class SoundnessTests(unittest.TestCase):
    """The guard must not claim more than the data supports, silently."""

    def test_every_alternative_states_what_it_commits_to_beyond_the_data(self):
        out = dc.synthesise_guard(
            [{"n": v} for v in (1, 2, 5, 10)],
            [{"n": v} for v in (0, -1, -5)],
        )
        self.assertTrue(out["commitment_beyond_the_data"])
        for alt in out["alternatives"]:
            self.assertTrue(alt["commitment_beyond_the_data"])

    def test_a_range_is_preferred_only_when_both_edges_are_decided(self):
        """Negatives on BOTH sides is what licenses a two-sided condition."""
        out = dc.synthesise_guard(
            [{"n": v} for v in (0, 100, 255)],
            [{"n": v} for v in (256, 300, -1)],
        )
        self.assertIn("between", out["guard"]["render"])
        self.assertIn("claims nothing outside", out["commitment_beyond_the_data"])

    def test_the_strict_edge_is_preferred_over_the_inclusive_one(self):
        """`gt max(negatives)` excludes the least; `ge min(positives)` more."""
        out = dc.synthesise_guard(
            [{"x": v} for v in (5, 6, 7)],
            [{"x": v} for v in (0, 1, 2)],
        )
        self.assertEqual("x gt 2", out["guard"]["render"])
        alternatives = [a["render"] for a in out["alternatives"]]
        self.assertIn("x ge 5", alternatives)

    def test_the_guard_is_actually_checked_on_every_example(self):
        positives = [{"n": v} for v in (1, 2, 5, 10)]
        negatives = [{"n": v} for v in (0, -1, -5)]
        out = dc.synthesise_guard(positives, negatives)
        guard = dc.Guard(
            [(a["feature"], a["op"], tuple(a["operand"]) if a["op"] == "between" else a["operand"])
             for a in out["guard"]["atoms"]]
        )
        self.assertTrue(all(guard.holds(p) for p in positives))
        self.assertFalse(any(guard.holds(n) for n in negatives))

    def test_the_claim_is_bounded(self):
        out = dc.synthesise_guard([{"n": 1}], [{"n": 0}])
        self.assertEqual(
            "SHORTEST_CONJUNCTION_THAT_SEPARATES_THESE_EXAMPLES", out["claim"]
        )
        self.assertEqual("THE_CONDITION", out["not_claimed"])
        self.assertEqual("NONE", out["authority"])


class ClosingTheGapTests(unittest.TestCase):
    """The loop that makes synthesis evidence-driven instead of guesswork."""

    def test_a_guard_names_what_it_guesses(self):
        out = dc.synthesise_guard(
            [{"n": v} for v in (0, 1, 128, 255)], [{"n": 256}]
        )
        self.assertEqual("n lt 256", out["guard"]["render"])
        self.assertIn("below", out["commitment_beyond_the_data"])

    def test_a_guard_names_the_probe_that_would_remove_the_guess(self):
        out = dc.synthesise_guard(
            [{"n": v} for v in (0, 1, 128, 255)], [{"n": 256}]
        )
        asks = [p["ask"] for p in out["next_probes"]]
        self.assertEqual(["is n = -1 accepted?"], asks)

    def test_answering_the_probe_closes_the_distinction(self):
        """One question, asked of the world, turns a guess into a range."""
        positives = [{"n": v} for v in (0, 1, 128, 255)]
        negatives = [{"n": 256}]
        before = dc.synthesise_guard(positives, negatives)
        self.assertEqual("n lt 256", before["guard"]["render"])

        negatives.append({"n": -1})  # the answer the module asked for
        after = dc.synthesise_guard(positives, negatives)
        self.assertEqual("n between 0 and 255", after["guard"]["render"])
        self.assertIn("claims nothing outside", after["commitment_beyond_the_data"])

    def test_a_probe_is_never_a_question_already_answered(self):
        """The loop asked the same thing eight times before this was fixed."""
        out = dc.synthesise_guard(
            [{"n": v} for v in (0, 1, 128, 255)], [{"n": 256}]
        )
        for probe in out["next_probes"]:
            self.assertNotIn("256", probe["ask"])

    def test_the_loop_converges_on_a_bounded_condition_in_three_rounds(self):
        """Two questions to decide both edges of 0..255, starting from noise."""
        human = lambda n: 0 <= n <= 255
        positives = [{"n": v} for v in (0, 1, 128, 255)]
        negatives = [{"n": -27}, {"n": 26}, {"n": 256}]
        # round 0 refuses: 26 sits inside the span, so no single atom separates
        self.assertEqual(
            "REFUSED__NO_DISCRIMINATING_FEATURE",
            dc.synthesise_guard(positives, negatives)["status"],
        )
        # the module cannot proceed until the offending evidence is removed, and
        # removing it is the caller's job: the examples were inconsistent, not the
        # synthesis. With evidence that has no negative inside the span:
        clean = [{"n": v} for v in (-5, 256)]
        first = dc.synthesise_guard(positives, clean)
        self.assertEqual("PASS__GUARD_SYNTHESISED", first["status"])
        asked = [p["ask"] for p in first["next_probes"]]
        self.assertTrue(asked)
        # answer the first question with the world's rule, then re-synthesise
        value = int(asked[0].split("=")[1].split()[0])
        (positives if human(value) else clean).append({"n": value})
        second = dc.synthesise_guard(positives, clean)
        self.assertEqual("PASS__GUARD_SYNTHESISED", second["status"])

    def test_an_unbounded_condition_never_converges_and_says_so(self):
        """No number of examples closes an open upper edge. Reported, not hidden."""
        positives = [{"d": v} for v in (1, 2, 99)]
        negatives = [{"d": v} for v in (-99, 1000)]
        out = dc.synthesise_guard(positives, negatives)
        self.assertEqual("PASS__GUARD_SYNTHESISED", out["status"])
        self.assertTrue(out["next_probes"], "the open edge stays open")

    def test_strings_get_no_numeric_probe(self):
        out = dc.synthesise_guard(
            [{"s": v} for v in ("a", "b", "c")], [{"s": ""}]
        )
        self.assertEqual("PASS__GUARD_SYNTHESISED", out["status"])
        for probe in out["next_probes"]:
            self.assertNotIn("+", probe["ask"])


class BranchEmissionTests(unittest.TestCase):
    def test_the_missing_branch_is_written_out_as_a_proposal(self):
        out = dc.branch_from_outcomes(
            [{"n": v} for v in (1, 2, 5)],
            [{"n": v} for v in (0, -1)],
        )
        self.assertEqual("PASS__GUARD_SYNTHESISED", out["status"])
        self.assertIsNotNone(out["source"])
        self.assertIn("if ", out["source"])
        self.assertIn("raise", out["source"])

    def test_the_body_is_not_claimed_to_be_derived(self):
        """The condition comes from the examples; the body comes from the demand."""
        out = dc.branch_from_outcomes([{"n": 1}], [{"n": 0}])
        self.assertIn("not", out["note"])
        self.assertIn("demanded outcome", out["note"])

    def test_a_refused_guard_emits_no_source(self):
        out = dc.branch_from_outcomes([{"n": 1}], [])
        self.assertIsNone(out["source"])
        self.assertEqual("REFUSED__NEEDS_BOTH_POLARITIES", out["status"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
