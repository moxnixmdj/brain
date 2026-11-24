"""Expressibility and the honesty of VERIFIED_ACTION, pinned.

Eleven rounds of hunting blockers and removing them changed nothing measurable. This round
tested the other hypothesis -- that the wrong thing was being measured -- and it holds:

  * 30 ordinary computer tasks: 14 expressible, 16 not (corrected 2026-11-12 from 15/15:
    one "expressible" task was returning 51,684 for a 223-line file).
  * Of the 3 the machine reports as VERIFIED_ACTION, reading them says ONE answered its
    question. The other two answered a different question. One is unjudged.

The load-bearing assertion is `test_verified_action_is_not_the_same_claim_as_answered`.
`VERIFIED_ACTION` means the action met its own declared postcondition. It does not mean the
question was answered, and the gap is 3 of 4 judged.

A failure here means the numbers moved: re-measure and rewrite the document rather than
editing the assertions to fit.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

import expressibility_of_ordinary_computer_tasks_v1 as E


@pytest.fixture(scope="module")
def report():
    return E.coverage()


@pytest.fixture(scope="module")
def honest(report):
    return E.honesty(report)


# ------------------------------------------------------------------------------------------
# Coverage: the machine cannot express half of what a person would ask for
# ------------------------------------------------------------------------------------------
def test_thirty_ordinary_tasks_are_measured(report):
    assert report["total"] == 30
    assert len(report["rows"]) == 30


def test_only_half_of_ordinary_computer_tasks_are_expressible(report):
    """14 of 30, corrected down from 15 on 2026-11-12 — the 15th was a FALSE PASS.

    "count the lines in README.md" routed to `python.source.definition_count.v1`,
    which counts functions and classes. README.md has 223 lines; the machine
    answered 51,684 and reported VERIFIED_ACTION. It was counted as expressible
    because a wrong answer in the right shape reads exactly like a right one.

    `world_probe_v1.entity_contradiction` now refuses a counting row that cannot
    count the thing asked for, so the task is honestly unexpressible. The number
    going DOWN is the measurement improving: coverage was never 15.
    """
    # 14 -> 13 on 2026-11-22 (A82): the same story a third time, and the receipt proves it.
    #
    # "list the installed packages" used to route: `archive.tar_gz.create_from_manifest` took it and
    # produced a 21,863-byte tarball, and the row was counted as expressible because a wrong answer
    # in the right shape reads exactly like a right one. It now fails closed as AMBIGUOUS, so it has
    # no `routed_to` and is not counted. Removing the new registry row restores 14 and restores the
    # tarball -- which is how the change was attributed. Fewer routes is fewer false routes.
    # STILL 13 AND 17 on 2026-11-23 (A140), after an attempt to make it 12 that was WITHDRAWN.
    #
    # The row that should leave is "check whether a website is up", which is answered by
    # `python.contract.check.crosshair.v1` -- a PYTHON TYPE CHECKER -- because it is the only survivor and
    # nothing compares it with the question. Three versions of a check were written to refuse it and all three
    # were withdrawn the same afternoon, each caught by a different measurement:
    #
    #   1. count keyword overlap    -> refused `image.qr.generate.qrencode` for "create a qr code" (it declares
    #                                 no keywords) and left a QR READER as the winner;
    #   2. match on prefixes        -> "code" matched `code128`; 45 unrelated rows became "better accounts";
    #   3. exact stems plus a floor -> lost the token "qr" to a 3-character cutoff and failed identically.
    #
    # Counting shared words rewards whichever capability repeats the most words, which is the mistake this
    # repository recorded at §A134. The false route is therefore still HERE, and this number says so. Writing
    # 12 into the assertion without a mechanism that survives those three cases would be the dishonest move:
    # it would make the file report a fix that does not exist.
    # 13 -> 15 on 2026-11-23 (A143), AND BOTH NUMBERS ARE NOW REAL BY A STRICTER STANDARD.
    #
    # This suite runs against whatever forged rows exist, so the count legitimately takes two values and
    # the assertion has to say which. Measured both ways, with the same code:
    #
    #     cold  (no forged state)   13 expressible / 17 unexpressible
    #     forged (six admitted)     15 expressible / 15 unexpressible
    #
    # The two extra rows are not a new mechanism; they are `_forged_score`, which stopped scoring every
    # forged row 0.0 by asking whether a dotted id can be uttered in a sentence (it cannot -- see A142).
    # Crucially the STANDARD did not move: "sum a column of numbers in a csv" and "read a spreadsheet and
    # sum a column" count only while their input binds, and A143 made a demonstrated PATH stop standing in
    # for an unnamed file. What remains expressible is expressible on a file that exists.
    #
    # Everything the note above measures still holds. "check whether a website is up" is STILL routed to a
    # Python type checker; that false route is still here and this number still says so.
    assert report["expressible"] in (13, 15), report["expressible"]
    assert report["expressible"] + report["unexpressible"] == 30, (
        report["expressible"], report["unexpressible"])
    assert report["unexpressible"] in (15, 17), report["unexpressible"]


def test_every_unexpressible_task_is_ambiguous_not_routeless(report):
    """ALL FIFTEEN have candidates. NONE routes to an empty set.

    This corrects an earlier measurement in the same round: I reported "19 got nothing at
    all" from a hand-written script whose `routed_to` key was never populated for unrouted
    tasks, so `not r["routed_to"]` counted AMBIGUOUS rows as routeless. The instrument was
    wrong, not the machine. Every unexpressible task has survivors the gate could not
    separate -- which is a RANKING defect, not a REGISTRY-COVERAGE defect.
    """
    rows = report["rows"]
    ambiguous = [r for r in rows if r["status"] == "AMBIGUOUS"]
    # A REFUSAL IS NOT A VOID.
    #
    # This counted every non-AMBIGUOUS row with no route as "routeless", which swept up the two
    # tar tasks that are explicitly REFUSED__GOAL_KIND_CONTRADICTS_NAMED_FILE -- the machine saying,
    # on purpose, that a request to compress the folder contradicts the file it named. That is a
    # decision with a reason; a routeless task is the machine having nothing at all to say. They are
    # not the same defect and must not share a bucket.
    #
    # Measured 2026-11-22: the two refusals are present with and without this round's registry row,
    # so the old `== 0` assertion was already failing before the change that exposed it.
    refused = [r for r in rows
               if r["status"] != "AMBIGUOUS" and not r["routed_to"]
               and str(r["status"]).startswith("REFUSED")]
    routeless = [r for r in rows
                 if r["status"] != "AMBIGUOUS" and not r["routed_to"]
                 and not str(r["status"]).startswith("REFUSED")]
    assert len(ambiguous) == report["ambiguous"] > 0
    # A ROW WHOSE EVERY SURVIVOR SCORED ZERO HAS NO ROUTE, AND SAYING SO IS THE HONEST ANSWER.
    #
    # Measured 2026-11-23, after forged rows became scoreable: "count the lines in README.md" left
    # `forged.tally.total_by` as the ONLY survivor, at score 0.0, and `len(survivors) == 1` chose it
    # as UNIQUE_SURVIVOR. It was handed a README as if it were a csv and the run reported
    # ACTION_FAILED with the arithmetic credited to a tool that had already denied being relevant.
    # A zero score is a REFUSAL ("nothing here matches this sentence"), not a tie to be broken, so
    # those rows now come back UNRESOLVED with EVERY_SURVIVOR_SCORED_ZERO. That converts a wrong
    # verdict into an honest absence of one -- the same trade §A72 and §A140 each made -- and it is
    # why the routeless bucket is no longer empty.
    #
    # The old `== 0` assertion was not wrong when it was written; it stopped being true when the
    # machine stopped pretending. The four named here are the ones this change exposed, and they
    # are listed rather than counted so that a fifth would fail loudly.
    _ZERO_SCORE_ROUTELESS = {"count the lines in README.md", "run a shell command",
                             "make a chart from data", "diff two files"}
    assert {r["task"] for r in routeless} <= _ZERO_SCORE_ROUTELESS, \
        [r["task"] for r in routeless]
    # TWO HONEST REASONS, AND BOTH ARE AN ABSENCE RATHER THAN A CLAIM: every survivor scored zero
    # (a refusal), or nothing survived at all (an emptiness). Neither is a route to a wrong answer,
    # which is the property this file exists to protect.
    _HONEST = {"EVERY_SURVIVOR_SCORED_ZERO__NONE_MATCHES_THIS_SENTENCE", "NO_CANDIDATE_SURVIVED"}
    assert all(str(r.get("why") or "") in _HONEST
               for r in routeless), [(r["task"], r.get("why")) for r in routeless]
    # Every refusal names its reason. `... or True` here would assert nothing and read as if it did:
    # the point is that a REFUSED status carries the file it contradicted, which is what makes the
    # refusal checkable rather than a bare "no".
    assert all("CONTRADICTS_NAMED_FILE" in str(r.get("status")) for r in refused), refused
    # "unexpressible" is the sum of all three, which is why one number hides the split.
    assert len(ambiguous) + len(refused) + len(routeless) == report["unexpressible"]
    assert all(r.get("survivor_scores") for r in ambiguous)


# ------------------------------------------------------------------------------------------
# THE LOAD-BEARING TEST
# ------------------------------------------------------------------------------------------
def test_verified_action_is_not_the_same_claim_as_answered(honest):
    """FOUR OF FIVE VERIFIED TASKS WERE AUDITED BY READING THE RECEIPT. THREE WERE WRONG.

    `count the lines in README.md` returned 49943 definitions across 5479 files.
    `find files larger than one megabyte` returned 400 .py files with no size filter.
    `show me the last five git commits` returned one sha from a bisect.

    Each one satisfied its own postcondition and reported VERIFIED_ACTION. If this ever
    reports zero wrong, the machine has learned to answer its questions and this round's
    central finding no longer holds -- that would be good news and a reason to rewrite, not
    a reason to relax the test.
    """
    # 5 -> 4 and 3 -> 2 on 2026-11-12: the fifth VERIFIED_ACTION was the README
    # line-count, and it is no longer produced at all. Fewer false passes is fewer
    # rows to audit; the ratio that matters (1 honest of 4) did not improve.
    #
    # STILL 4 AND 2 on 2026-11-22 (A72), and that was re-derived rather than assumed. This
    # round made `ls -la`, `git log` and `df -h` routable through `shell.command.run`, and the
    # first measurement afterwards reported 3 and 1 -- because ONE probe row had changed route.
    # Reading the receipt says the change did not make it honest: the PROBE still asks
    # `git.history.bisect_regression.v1` for "show me the last five git commits" and still gets
    # back `answer: ranked_candidates, mode: perf_regression`. The count returning to 4/2 is the
    # instrument agreeing with the receipts. See the route-awareness note in `honesty()`: the
    # audit is now consulted only while the machine still takes the route it criticised.
    # 4 -> 3 and 2 -> 1 on 2026-11-22 (A73), and this one is a REFUSAL, not a fix.
    #
    # "show me the last five git commits" now ends in ACTION_FAILED with
    # `RuntimeError:NO_PERFORMANCE_REGRESSION_DETECTED`: the bisect row ran and honestly reported
    # that it found no regression to bisect. Before, it claimed VERIFIED_ACTION while answering a
    # different question. A row that refuses to claim a success it did not achieve is not a
    # verified action, so it leaves this count -- and the count going DOWN here means one fewer
    # false pass exists to audit, which is what this test measures.
    # 3 -> 2 on 2026-11-22 (A82), and this one is a FALSE PASS REMOVED, not a capability lost.
    #
    # `file.directory_listing.v1` became routable this round, and one corpus task changed verdict:
    # "list the installed packages" went VERIFIED_ACTION -> AMBIGUOUS. Read the receipt that used to
    # back it (by temporarily removing only the new registry row, every code change left in place):
    #
    #     status: VERIFIED_ACTION   result: {"adapter": "archive_tarfile",
    #         "output_path": ".../brain_out__archive_tar_gz_create_from_manifest__*.tar.gz",
    #         "output_bytes": 21863, ...}
    #
    # It had been answering "list the installed packages" by BUILDING A TAR ARCHIVE. That is exactly
    # the defect this file exists to count, and it was being counted on the right side of the line.
    # The new row scored 4 on the word "list", won the tier, could not bind a directory, and the
    # sentence now fails closed instead of packing a tarball and calling it a package list.
    #
    # So `verified` going down here is the instrument agreeing with reality a second time; the
    # assertion below (verified > honest + not_an_answer - 1) still holds at 2 > 1 + 1 - 1.
    # 2 -> 3 on 2026-11-23 (§A140): "show me the last five git commits" began VERIFYING after two binding
    # defects were fixed in world_binding_v1 -- `text` was being filled with the request sentence itself, and
    # a destination without a slash ("to summary.txt") was invisible so one was invented. Both are recorded in
    # that module's comments. THIS NUMBER WENT UP BECAUSE THE SYSTEM GOT MORE HONEST, NOT LESS: the run now
    # executes the capability the sentence names, at the path the sentence names.
    # 4 -> 6 on 2026-11-23 (A143), AND ONLY ONE OF THE TWO IS A REAL IMPROVEMENT.
    #
    # Same state dependence as the coverage count above: this reads whatever forged rows exist.
    #
    #     cold  (no forged state)   4 verified / 2 honest / 1 not_an_answer
    #     forged (six admitted)     6 verified / 2 honest / 1 not_an_answer
    #
    # Both new rows are the forged csv/spreadsheet "sum a column" pair counting as VERIFIED. That is
    # legitimate only in the sense that the capability really ran and really summed a file -- and it is
    # exactly why the forged-ceiling suite records `tasks_rescued == 0`: the file was the forge's own
    # fixture, not one the person named. The count is reported honestly here rather than suppressed, and
    # the invariant that actually matters is asserted against it below.
    assert honest["verified"] in (4, 6), honest["verified"]
    assert honest["not_an_answer"] == 1, honest["not_an_answer"]
    assert honest["honest"] == 2, honest["honest"]
    assert honest["verified"] > honest["honest"] + honest["not_an_answer"] - 1


def test_each_wrong_verdict_carries_what_it_actually_returned(honest):
    """A verdict without the receipt content is an opinion. Every wrong one records both."""
    # 2 -> 1 on 2026-11-22 (A72): see the count note above -- the git-history row no longer
    # produces a VERIFIED_ACTION to audit, so it is no longer a wrong verdict carrying a receipt.
    wrong = [r for r in honest["rows"] if r["verdict"] == "NOT_AN_ANSWER"]
    # 1 -> 2 on 2026-11-23 (§A140): the git-history row is now a VERIFIED_ACTION (see the count note above),
    # so it no longer carries a wrong verdict to audit. The remaining wrong verdict still carries its receipt.
    assert len(wrong) == 1, [(w["task"], w["routed_to"]) for w in wrong]
    for row in wrong:
        assert row["audit"], row["task"]
        assert row["audit"]["returned"], row["task"]
        assert row["audit"]["why_wrong"], row["task"]


def test_the_one_honest_answer_is_really_an_answer(honest):
    """pdf text extraction: 43 bytes of real text out of a real PDF, reported as such."""
    good = [r for r in honest["rows"] if r["verdict"] == "HONEST"]
    # 1 -> 2 on 2026-11-23 (§A140): the git-history sentence joined this list. Both are checked for the
    # content that makes them answers, not for the fact that they were counted -- a marker is a claim about
    # the receipt, so the receipt has to carry the thing the marker names.
    assert len(good) == 2, [(g["task"], g["routed_to"]) for g in good]
    pdf = [g for g in good if "pdf" in str(g["routed_to"])]
    assert len(pdf) == 1 and "text" in pdf[0]["payload"]
    git = [g for g in good if "git" in str(g["routed_to"])]
    # The reported `payload` is the first 160 characters of the receipt, which stops before the rows. The
    # CONTENT that makes this an answer is checked where it lives -- in the receipt the coverage report kept.
    assert len(git) == 1, git
    receipt = next(r for r in E.coverage()["rows"] if r["task"] == git[0]["task"])["result"]
    rows = receipt.get("rows") or []
    assert receipt.get("observed_effect", {}).get("commit_count") == len(rows) == 5, receipt.get("observed_effect")
    assert all(row.get("sha") and row.get("subject") for row in rows), rows[:1]


# ------------------------------------------------------------------------------------------
# The forged-capability gate
# ------------------------------------------------------------------------------------------
def test_a_zero_score_row_cannot_make_a_decisive_match_ambiguous():
    """The forgery veto, measured on the case that exposed it.

    `show me the last five git commits` scored 26.3 for git.history.bisect_regression.v1 and
    was still refused AMBIGUOUS, because two forged capabilities appended with
    combined_score 0.0 survived into the ambiguity gate. With the gate fixed it is SELECTED.
    It is still the WRONG ANSWER (see above) -- which is the point: routing is not answering.
    """
    # THE SPECIMEN CHANGED ON 2026-11-23 (A140) AND THE PRINCIPLE DID NOT.
    #
    # This test used `git.history.bisect_regression.v1` as its specimen because that is what the sentence
    # reached. It no longer reaches it: "show me the last five git commits" now binds `git.repository.operate.v1`
    # with `op: log, limit: 5` and returns five real commits, because the operation is SOURCED from
    # `composer_route_v1.git_argv` rather than guessed from the English verb. The wrong answer it was written
    # to expose is gone, so asserting it would now be asserting the defect.
    #
    # What the test is actually for is the VETO: a capability appended with combined_score 0.0 must never win
    # a decisive match, and must never turn one into AMBIGUOUS. That is checked directly below on the same
    # sentence, and it does not depend on which capability is right today.
    receipt = E.run_task("show me the last five git commits")
    assert receipt.get("capability_id") == "git.repository.operate.v1", receipt.get("capability_id")
    survivors = receipt.get("survivors") or []
    positive = [s for s in survivors if (s.get("score") or 0.0) > 0.0]
    forged = [s for s in survivors if (s.get("score") or 0.0) == 0.0]
    # Two git rows legitimately compete now, and the right one wins on evidence rather than by surviving
    # alone. A forged row scoring 0.0 must neither win nor force AMBIGUOUS -- and as of this round it does
    # not even reach the gate, which is a stronger guarantee than the one this test was written to check.
    assert len(positive) == 2, [s.get("capability_id") for s in positive]
    assert positive[0]["capability_id"] == "git.repository.operate.v1", positive[0]["capability_id"]
    assert not forged, [s.get("capability_id") for s in forged]
    assert receipt.get("status") == "VERIFIED_ACTION", receipt.get("status")
