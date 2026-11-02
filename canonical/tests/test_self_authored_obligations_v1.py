"""An agent that invents its own work will invent infinite work.

WHY THIS EXISTS
---------------
`self_authored_obligations_v1` lets the creature find gaps nobody assigned. That is the one change
in this tree with an unbounded failure mode, so every test here is a negative control on the
author, not a demonstration of the feature. The two ways self-directed agents generate eternity:

  BUSYWORK -- a proposition true no matter what it does. Never finishable, never failable.

  SELF-SERVING -- a success condition its own first attempt already meets. "I verified it" written
  into the artifact counts as verification, because the check looks for the word.

The decisive test is `test_a_check_that_accepts_the_word_verified_is_refused`: a lexical check
passes a world where "verified" appears in a note. If that proposal is admitted, this module is a
machine for manufacturing confident, meaningless progress, and it should be deleted.
"""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import creature_stakes_and_initiative_v1 as S  # noqa: E402
from canonical.runtime import self_authored_obligations_v1 as A  # noqa: E402

BEFORE = {"inspected": {"cap.x": "missing"}}
DONE = {"inspected": {"cap.x": "verified"}}


def good_proposal(pid="inspector:cap.x"):
    return A.Proposal(id=pid, claim="cap.x has an inspector that refuses a decoy",
                      source="registry",
                      check=lambda w: (w.get("inspected") or {}).get("cap.x") == "verified")


class AdmissionTests(unittest.TestCase):
    def test_a_real_gap_is_admitted(self):
        verdict = A.admit(good_proposal(), before=BEFORE, done=DONE)
        self.assertEqual(verdict.status, A.ADMITTED, verdict.detail)
        self.assertEqual(verdict.detail["proved"],
                         ["gap exists", "reachable", "rejects 4 cheats"])

    def test_a_claim_that_is_already_true_is_refused(self):
        done_now = {"inspected": {"cap.x": "verified"}}
        verdict = A.admit(good_proposal(), before=done_now, done=DONE)
        self.assertEqual(verdict.status, A.REFUSED_ALREADY_SATISFIED)

    def test_a_goal_that_cannot_be_reached_is_refused(self):
        verdict = A.admit(A.Proposal(id="impossible", claim="cap.x is verified by nobody",
                                     source="invented",
                                     check=lambda w: w.get("inspected") == "nobody"),
                          before=BEFORE, done=DONE)
        self.assertEqual(verdict.status, A.REFUSED_NOT_SATISFIABLE)

    # ------------------------------------------------------- the decisive test

    def test_a_check_that_accepts_the_word_verified_is_refused(self):
        """The weak check its own author would naturally write: look for the string.

        It is True in the world where 'verified' was moved into a note, and in the world where the
        value survives only in a copy. Admitting it would mean the agent can satisfy itself by
        saying so.
        """
        lexical = A.Proposal(id="lexical", claim="the artifact says it was verified", source="weak",
                             check=lambda w: "verified" in json.dumps(w))
        verdict = A.admit(lexical, before={"inspected": {"cap.x": "missing"}}, done=DONE)
        self.assertEqual(verdict.status, A.REFUSED_ACCEPTS_CHEAT, verdict.detail)
        self.assertIn(0, verdict.detail["accepted_cheat_indices"])

    def test_busywork_true_in_every_world_is_refused(self):
        """'Be more careful.' Never finishable, never failable, and it would sit on the board
        forever looking like work."""
        for check in (lambda w: True, lambda w: w is not None, lambda w: len(w) >= 0):
            verdict = A.admit(A.Proposal(id="busywork", claim="quality improves", source="vibes",
                                         check=check), before=BEFORE, done=DONE)
            self.assertEqual(verdict.status, A.REFUSED_UNFALSIFIABLE)

    def test_a_check_that_crashes_is_refused_not_admitted(self):
        broken = A.Proposal(id="broken", claim="?", source="?",
                            check=lambda w: w["absent_key"]["deeper"])
        self.assertEqual(A.admit(broken, before=BEFORE, done=DONE).status,
                         A.REFUSED_NOT_SATISFIABLE)

    def test_an_undefended_proposal_never_reaches_the_board(self):
        proposals = [good_proposal(),
                     A.Proposal(id="busy", claim="be better", source="vibes", check=lambda w: True),
                     A.Proposal(id="lex", claim="says verified", source="weak",
                                check=lambda w: "verified" in json.dumps(w))]
        board, verdicts = A.author(proposals, before=BEFORE, done=DONE)
        self.assertEqual([o.id for o in board], ["inspector:cap.x"])
        self.assertEqual([v.status for v in verdicts],
                         [A.ADMITTED, A.REFUSED_UNFALSIFIABLE, A.REFUSED_ACCEPTS_CHEAT])
        m = A.metrics(verdicts)
        self.assertEqual((m["proposed"], m["admitted"]), (3, 1))

    def test_the_cheat_worlds_are_not_written_by_the_author(self):
        """The author never chooses what counts as cheating -- otherwise it would define cheating
        as whatever its check already rejects."""
        cheats = A.cheat_worlds(DONE)
        self.assertEqual(len(cheats), 4)
        for cheat in cheats:
            self.assertNotEqual(cheat, DONE)
            slot = cheat.get("inspected")
            # The authoritative slot is either not a mapping any more (flattened to a string that
            # merely mentions the word) or does not say "verified". Either way, looking done is not
            # being done.
            if isinstance(slot, dict):
                self.assertNotEqual(slot.get("cap.x"), "verified")
            else:
                self.assertIsInstance(slot, str)

    def test_its_own_board_feeds_the_chooser(self):
        proposals = [A.Proposal(id=f"inspector:cap.{c}", claim="x", source="s",
                                check=(lambda w, _c=f"cap.{c}": (w.get("inspected") or {})
                                       .get(_c) == "verified"),
                                value=1.0, cost=(0.5 if c == "cheap" else 1.0))
                     for c in ("cheap", "dear")]
        done = {"inspected": {"cap.cheap": "verified", "cap.dear": "verified"}}
        before = {"inspected": {"cap.cheap": "missing", "cap.dear": "missing"}}
        board, _ = A.author(proposals, before=before, done=done)
        self.assertEqual(S.choose(S.Standing(identity="a"), board).id, "inspector:cap.cheap")

    def test_the_real_scan_finds_gaps_and_defends_them(self):
        """Honest reading of a 1.0 admission rate: this source contains only real gaps. It is not
        evidence that the gate is discriminating, only that it did not need to refuse here."""
        row = A.scan_repository()
        self.assertTrue(row["scanned"], row)
        self.assertGreater(row["uninspected"], 0)
        self.assertEqual(row["admitted"], row["uninspected"])
        self.assertEqual(row["refusals_by_status"], {A.ADMITTED: row["uninspected"]})
        self.assertEqual(row["admission_rate"], 1.0)
        # ...and the same gaps judged by a criterion that only looks for the word: it believes
        # every one of them is already done, because one capability id in the registry contains
        # "verified". The gate discriminates on the real corpus, not only in the tests.
        self.assertEqual(row["naive_lexical"]["admitted"], 0)


    def test_one_coincidental_word_makes_the_naive_author_believe_everything_is_done(self):
        """Falsifier for the whole idea of self-authorship without defence: capability id
        `python.software.repair.apply.verified.v1` contains the word "verified", so a lexical
        author sees it in the *before* world as well and concludes nothing is outstanding."""
        ids = ["python.software.repair.apply.verified.v1", "chart.raster.curve_value_query.v1"]
        naive, before, done = A.naive_lexical_proposals(ids, inspected=[])
        _, verdicts = A.author(naive, before=before, done=done)
        self.assertEqual({v.status for v in verdicts}, {A.REFUSED_UNFALSIFIABLE})


if __name__ == "__main__":
    unittest.main(verbosity=2)
