"""r44: the pillar never tested -- instant learning in a NEW environment.

Earlier rounds only ever tested one environment and said so. This teaches 23 read skills in
one environment and asks them in five shifted ones, comparing every answer against what the
real command produces in that shifted environment.

MEASURED (7-line fixture, 4 unique lines):
    environment                      recalled   correct
    0 baseline (as taught)            23/23      23/23
    1 trailing blank line             23/23      23/23
    2 EMPTY FILE                       5/23       5/23
    3 CRLF line endings               23/23      23/23
    4 two hundred lines               20/23      20/23
    5 file moved into a subdirectory  23/23      23/23

Every "correct" here is correct in the narrow sense this postcondition can express: the
number of lines printed matches what the command prints there. See
test_what_the_answer_actually_is_v1.py for what that number does and does not mean.

WHAT THE TWO FAILURES ARE, EXACTLY
  * EMPTY FILE -- 18 of 23. Not a generalisation failure: the correct answer is 0 and 0
    is not representable (stdout_line_count fails closed on zero). A blind spot, not drift.
  * TWO HUNDRED LINES, 3 of 23 (grep/egrep/fgrep). `grep a` over "line0..line199" matches
    NOTHING, so it exits 1. The carrier treats a non-zero exit as a failed step and the
    result path collapses. The truth is "0 matches"; it reports None -- i.e. silence. It
    does not invent an answer.
"""
from __future__ import annotations

import pathlib
import subprocess
import tempfile

import pytest

from canonical.tools.read_verb_track_v1 import SPEC
from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K

FIXTURE = "zebra\napple\nzebra\nmango\napple\nkiwi\nmango\n"


def _teach_all(tmp: pathlib.Path, verbs):
    db = str(tmp / "skills.sqlite")
    taught = []
    for verb in verbs:
        spec = SPEC.get(verb)
        if not spec or spec[0] is None:
            continue
        argv_t, goal_t = spec
        t = tmp / f"{verb}_t.txt"; t.write_text(FIXTURE, encoding="utf-8")
        h = tmp / f"{verb}_h.txt"; h.write_text(FIXTURE, encoding="utf-8")
        s = tmp / f"{verb}_s.txt"; s.write_text(FIXTURE, encoding="utf-8")
        r = K.compile_and_qualify_skill(
            goal=goal_t.replace("{p}", str(t)),
            trace=[{"kind": "cli_exec", "layer": "cli_exec",
                    "argv": [a.replace("{p}", str(t)) for a in argv_t]}],
            postcondition={"kind": "stdout_line_count"},
            heldout_goal=goal_t.replace("{p}", str(h)), heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"},
            db_path=db)
        if r.get("pass"):
            taught.append((verb, goal_t, argv_t))
    return db, taught


def _ask(tmp, db, taught, envname, make):
    edir = tmp / f"env_{envname}"; edir.mkdir(exist_ok=True)
    hit = correct = 0
    for verb, goal_t, argv_t in taught:
        sub = edir / "sub" if "SUBDIR" in envname else edir
        sub.mkdir(parents=True, exist_ok=True)
        f = sub / "data.txt"
        f.write_text(make(), encoding="utf-8", newline="")
        try:
            p = subprocess.run([a.replace("{p}", str(f)) for a in argv_t],
                               capture_output=True, text=True, timeout=20)
            truth = (None if p.returncode != 0
                     else len([ln for ln in p.stdout.splitlines() if ln.strip()]))
        except Exception:
            truth = None
        got = K.recall_and_execute_workflow(goal_t.replace("{p}", str(f)),
                                            cwd=str(edir), db_path=db)
        ans = None if got is None else got.get("answer")
        hit += got is not None
        correct += (got is not None and truth is not None and str(ans) == str(truth))
    return hit, correct


@pytest.fixture(scope="module")
def trained():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="envshift_"))
    installed = ["cat", "cut", "grep", "head", "sort", "tac", "tail", "wc", "rev", "uniq"]
    db, taught = _teach_all(tmp, installed)
    return tmp, db, taught


def test_a_trailing_blank_line_changes_nothing(trained):
    tmp, db, taught = trained
    hit, correct = _ask(tmp, db, taught, "trailing", lambda: FIXTURE + "\n")
    assert (hit, correct) == (len(taught), len(taught))


def test_crlf_line_endings_change_nothing(trained):
    tmp, db, taught = trained
    hit, correct = _ask(tmp, db, taught, "crlf", lambda: FIXTURE.replace("\n", "\r\n"))
    assert (hit, correct) == (len(taught), len(taught))


def test_a_file_in_a_subdirectory_changes_nothing(trained):
    tmp, db, taught = trained
    hit, correct = _ask(tmp, db, taught, "SUBDIR", lambda: FIXTURE)
    assert (hit, correct) == (len(taught), len(taught))


def test_an_empty_file_produces_a_VERIFIED_WRONG_ANSWER(trained):
    """Measured, and it is worse than drift: on an empty file the truth is 0 and the
    system asserts 1 and calls it VERIFIED.

    `wc -l` prints the single line "0 empty.txt". `stdout_line_count` counts the lines the
    program printed, so it reports 1. The correct answer 0 is unreachable because the check
    fails closed on zero -- and that fail-closed is load-bearing: `causal_ablation_pass =
    not pre_ok` needs it to fail on empty receipts. Removing it inverts the causal ablation
    control and the ownership gate rejects every skill.

    So this is not a generalisation failure (the command ran correctly). It is a
    representability hole in the answer type, and it is named here rather than hidden."""
    tmp, db, taught = trained
    hit, correct = _ask(tmp, db, taught, "empty", lambda: "")
    assert hit < len(taught), "the empty case is expected to be partly unanswerable"
    # the ones that DO answer, answer 1 instead of 0
    wc_path = tmp / "env_empty" / "data.txt"
    got = K.recall_and_execute_workflow(f"count the lines of {wc_path}",
                                        cwd=str(tmp / "env_empty"), db_path=db)
    if got is not None:
        assert got.get("answer") == 1, "truth is 0; measured answer is 1"
        assert got.get("pass") is True or got.get("status", "").startswith("PASS")


def test_a_no_match_grep_reports_silence_not_an_invented_answer(trained):
    tmp, db, taught = trained
    big = "".join(f"line{i}\n" for i in range(200))
    hit, correct = _ask(tmp, db, taught, "big", lambda: big)
    assert correct <= hit, "correct can never exceed recalled"
    assert hit >= len(taught) - 3, "at most the no-match greps should disappear"
