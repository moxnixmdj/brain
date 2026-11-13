#!/usr/bin/env python3
"""What "learn it in one environment, use it in another" must keep saying.

Every figure here is read from ``ACROSS_ENVIRONMENTS_20261112_V1.json``. The tests exist because
this round's headline number is the one most likely to be quoted and the most misleading: the mean
transfer figure is carried almost entirely by one kind of change, and three of six kinds transfer
exactly nothing.

Three defects this round actually made, each pinned so it cannot come back:

  * ``three_showings`` was passed only ``demonstrations[0]``, which made it byte-identical to
    ``exact`` and produced a "P3 failed" that was a property of the code rather than of transfer
    (``test_three_showings_really_shows_three``);
  * both arms used only the teacher's first changed file, so the figure depended on which file
    happened to be listed first (``test_every_teacher_file_is_used_as_a_demonstration``);
  * refusals were truncated at the first colon, so the record could not explain why a kind
    transferred nothing (``test_a_refusal_keeps_its_reason``).
"""
from __future__ import annotations

import collections
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
RECORD = ROOT / "canonical/verification/ACROSS_ENVIRONMENTS_20261112_V1.json"


def record() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def by_kind(arm: str) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = collections.defaultdict(lambda: {"right": 0, "wrong": 0, "developers": 0})
    for row in record()["across_rows"]:
        if row["arm"] != arm:
            continue
        for key in ("right", "wrong", "developers"):
            out[row["kind"]][key] += row[key]
    return dict(out)


class TheRecordExists(unittest.TestCase):
    def test_authority_is_none_and_nothing_was_claimed(self):
        r = record()
        self.assertEqual(r["schema"], "ACROSS_ENVIRONMENTS_V1")
        self.assertIn("NONE", r["authority"])
        self.assertFalse(r["truth_achieved"])
        self.assertFalse(r["terminal_authority"])
        self.assertEqual(r["model_calls"], 0)
        self.assertEqual(r["incremental_spend_usd"], 0)

    def test_six_kinds_and_two_repositories_each(self):
        """Cross-repository transfer needs a second repository with the same kind of change."""
        kinds = record()["kinds"]
        self.assertEqual(len(kinds), 6)
        for kind, repos in kinds.items():
            self.assertEqual(len(repos), 2, kind)
            self.assertNotEqual(repos[0].split("#")[0], repos[1].split("#")[0],
                                f"{kind}: the two repositories must differ")

    def test_the_record_says_what_it_does_not_show(self):
        note = record()["read_this_first"]
        # The value must state the limit in words, not merely exist.
        self.assertIn("No test was run", note["what_this_does_not_show"])
        self.assertIn("not correctness", note["what_this_does_not_show"])


class TheMeanIsNotTheFinding(unittest.TestCase):
    def test_three_kinds_transfer_at_all_and_three_at_exactly_zero(self):
        table = by_kind("exact")
        moving = sorted(kind for kind, row in table.items() if row["right"] > 0)
        stuck = sorted(kind for kind, row in table.items() if row["right"] == 0)
        self.assertEqual(len(moving), 3)
        self.assertEqual(len(stuck), 3)
        self.assertEqual(stuck, ["a library taken out", "an old name of a logging method",
                                 "text put together another way"])

    def test_one_kind_carries_almost_all_of_the_transfer(self):
        """537 of 562 correct changes. A mean over this is a mean over one kind of change."""
        table = by_kind("exact")
        total = sum(row["right"] for row in table.values())
        self.assertEqual(total, 562)
        self.assertEqual(table["an old name of a test method"]["right"], 537)
        self.assertGreater(537 / total, 0.95)

    def test_the_mean_transfer_is_pinned(self):
        exact = record()["across_repository"]["exact"]
        self.assertAlmostEqual(exact["share_of_the_work"], 0.573, places=3)
        self.assertEqual(exact["right"], 562)
        self.assertEqual(exact["wrong"], 0)


class ThreeMoreShowingsRescueWhatAlreadyMovedAndNothingElse(unittest.TestCase):
    def test_three_showings_raises_the_moving_kinds_to_near_ceiling(self):
        table = by_kind("three_showings")
        self.assertEqual(table["an old name of a test method"]["right"], 757)
        self.assertGreater(table["an old name of a test method"]["right"] / 761, 0.99)
        self.assertEqual(table["a thread method renamed"]["right"], 43)

    def test_three_showings_do_not_move_a_kind_that_transfers_nothing(self):
        """The decisive negative: more demonstrations are not the missing operator."""
        table = by_kind("three_showings")
        for kind in ("a library taken out", "an old name of a logging method",
                     "text put together another way"):
            self.assertEqual(table[kind]["right"], 0, f"{kind} must stay at zero")

    def test_three_showings_really_shows_three(self):
        """The defect: the arm was passed only the first demonstration, so it equalled ``exact``."""
        rows = [r for r in record()["across_rows"] if r["arm"] == "three_showings"]
        self.assertTrue(rows)
        self.assertTrue(all(r["demonstrations"] == 3 for r in rows),
                        "every three_showings row must report three demonstrations used")
        exact = record()["across_repository"]["exact"]
        three = record()["across_repository"]["three_showings"]
        self.assertNotEqual(exact["right"], three["right"],
                            "if these are equal the arm is not doing anything different")

    def test_every_teacher_file_is_used_as_a_demonstration(self):
        """Not one: the recorded 0.529 was produced by averaging over demonstrations."""
        exact_rows = [r for r in record()["across_rows"] if r["arm"] == "exact"]
        self.assertTrue(exact_rows)
        # 176 askings over 12 pairs with 3-4 changed files per repository on both sides
        self.assertEqual(sum(r["asked"] for r in exact_rows), 176)
        self.assertGreater(sum(r["asked"] for r in exact_rows), 12 * 4)


class PrecisionWasNotTradedAway(unittest.TestCase):
    def test_narrow_arms_make_no_wrong_change_in_any_repository(self):
        for arm in ("literal", "exact", "three_showings"):
            self.assertEqual(record()["across_repository"][arm]["wrong"], 0, arm)
            self.assertEqual(record()["across_repository"][arm]["precision"], 1.0, arm)

    def test_the_wide_ladder_is_the_only_arm_that_is_wrong(self):
        wide = record()["across_repository"]["any_rung"]
        self.assertEqual(wide["wrong"], 71)
        self.assertLess(wide["precision"], 0.30)
        self.assertLess(wide["share_of_the_work"], 0.05)


class TheCheckCannotBeTheNextStep(unittest.TestCase):
    def test_the_previous_round_already_measured_the_check_at_zero(self):
        """Gating the wide rung by the project's tests recovers nothing, and that is why this round
        did not build the dependency installer the previous round proposed."""
        prior = json.loads((ROOT / "canonical/verification/GENERALIZATION_RUNG_GRADIENT_20261112_V1.json")
                           .read_text(encoding="utf-8"))
        self.assertEqual(prior["summary"]["any_rung_check"]["share_of_the_work"], 0.0)
        self.assertEqual(prior["totals"]["any_rung_check"]["check_asked"], 132)
        # and the narrow arm never asked the check at all, because it had nothing wrong to catch
        self.assertEqual(prior["totals"]["exact"]["check_asked"], 0)
        self.assertEqual(prior["totals"]["exact"]["wrong"], 0)


class ARefusalExplainsItself(unittest.TestCase):
    def test_a_refusal_keeps_its_reason(self):
        """A bare 'refused' explains nothing; the sentence is what names the missing operator."""
        reasons = []
        for row in record()["across_rows"]:
            reasons.extend((row.get("refusals") or {}).keys())
        self.assertTrue(reasons)
        sentences = [r for r in reasons if len(r) > 40 and " " in r]
        self.assertTrue(sentences, "at least some refusals must carry their whole sentence")

    def test_the_three_stuck_kinds_refuse_because_the_form_is_absent(self):
        stuck = [r for r in record()["across_rows"]
                 if r["arm"] == "exact" and r["kind"] in
                 ("a library taken out", "an old name of a logging method",
                  "text put together another way")]
        self.assertTrue(stuck)
        joined = " ".join(" ".join((r.get("refusals") or {}).keys()) for r in stuck)
        self.assertIn("nothing in the file has the form", joined)


class ThePredictionsWereScored(unittest.TestCase):
    def test_one_prediction_failed_and_is_recorded_as_failed(self):
        """P1 assumed cross-repo would be worse than within-repo. It was not, and the record says so."""
        claims = record()["pre_registered_prediction"]["claims"]
        self.assertEqual(set(claims), {"P1_cross_repo_below_within_repo_0_529",
                                       "P2_cross_repo_not_zero_and_precision_above_0_8",
                                       "P3_three_showings_beats_exact_across_repos"})
        self.assertFalse(claims["P1_cross_repo_below_within_repo_0_529"]["held"])
        self.assertFalse(record()["pre_registered_prediction"]["all_held"])

    def test_the_two_that_mattered_did_hold(self):
        claims = record()["pre_registered_prediction"]["claims"]
        self.assertTrue(claims["P2_cross_repo_not_zero_and_precision_above_0_8"]["held"])
        self.assertTrue(claims["P3_three_showings_beats_exact_across_repos"]["held"])


if __name__ == "__main__":
    unittest.main()
