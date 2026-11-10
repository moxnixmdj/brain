"""r46: the GOAL chooses the answer type, and "no match" is an answer.

TWO THINGS WERE WRONG, AND BOTH WERE MINE.

1. THE TEACHER CHOSE THE TYPE. Every skill in the track was taught with
   postcondition={"kind":"stdout_line_count"}, so every verb answered "how many lines did
   the program print". 'sha256 of <f>' answered 1. Now `postcondition=None` lets
   `infer_contract_from_goal` read the goal: 'sha256 of' -> the hash, 'how many' -> an
   integer, 'first two lines' / 'unique lines' / 'lines containing' -> the lines.

2. "NO MATCH" WAS A CRASH. `grep PATTERN f` exits 1 when nothing matches. The carrier
   treated ANY non-zero exit as a failed step, so a legitimate empty answer became
   FAIL_CLOSED and the skill could not even be taught on a file with no matches.

MEASURED, teaching all 23 verbs with postcondition=None and asking on an unseen file:
    1/23 answers matched the real command before r45's typed answers
   20/23 after goal-driven inference
   23/23 after empty-result handling
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K
from canonical.runtime import admitted_confinement_execution_v1 as A


# ------------------------------------------------------------ the goal decides
@pytest.mark.parametrize("goal,expected", [
    ("count the lines of /tmp/f", "stdout_integer_value"),
    ("how many unique lines in /tmp/f", "stdout_integer_value"),
    ("sha256 of /tmp/f", "stdout_first_token"),
    ("md5 of /tmp/f", "stdout_first_token"),
    ("checksum /tmp/f", "stdout_first_token"),
    ("first two lines of /tmp/f", "stdout_lines"),
    ("unique lines of /tmp/f", "stdout_lines"),
    ("lines containing a in /tmp/f", "stdout_lines"),
    ("dump the contents of /tmp/f", "stdout_lines"),
    ("reverse each line of /tmp/f", "stdout_lines"),
])
def test_the_goal_names_the_answer_type(goal, expected):
    assert K.infer_contract_from_goal(goal)["kind"] == expected


def test_an_empty_goal_falls_back_to_text_rather_than_guessing_a_number():
    assert K.infer_contract_from_goal("")["kind"] == "stdout_text"


# ------------------------------------------------------- no match is an answer
def test_grep_exit_one_is_empty_not_broken():
    assert A.exit_one_means_empty("grep", 1) is True
    assert A.exit_one_means_empty("egrep", 1) is True
    assert A.exit_one_means_empty("fgrep", 1) is True


def test_a_real_breakage_is_still_a_breakage():
    """The narrow rule must not swallow genuine failures."""
    assert A.exit_one_means_empty("wc", 1) is False
    assert A.exit_one_means_empty("cat", 1) is False
    assert A.exit_one_means_empty("grep", 2) is False      # 2+ always fails
    assert A.exit_one_means_empty("sort", 1) is False


def test_missing_file_and_no_match_are_distinguishable():
    import tempfile as _t
    with _t.TemporaryDirectory() as td:
        w = pathlib.Path(td)
        (w / "d.txt").write_text("a\nb\n", encoding="utf-8")
        miss = A.execute_confined(["wc", "-l", "nosuch.txt"], workspace_root=str(w))
        nomatch = A.execute_confined(["grep", "zzz", "d.txt"], workspace_root=str(w))
        assert miss.get("empty_result") is False, "a missing file is not an empty answer"
        assert nomatch.get("empty_result") is True
        assert (w / "d.txt").exists()


# ---------------------------------------------------------------- end to end
def test_a_skill_taught_about_matches_answers_empty_when_there_are_none():
    with tempfile.TemporaryDirectory() as td:
        w = pathlib.Path(td)
        db = str(w / "s.sqlite")
        t = w / "t.txt"; t.write_text("zebra\nzzz line\n", encoding="utf-8")
        h = w / "h.txt"; h.write_text("zebra\nzzz line\n", encoding="utf-8")
        s = w / "s.txt"; s.write_text("x\n", encoding="utf-8")
        r = K.compile_and_qualify_skill(
            goal=f"lines containing zzz in {t}",
            trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": ["grep", "zzz", str(t)]}],
            postcondition=None,
            heldout_goal=f"lines containing zzz in {h}", heldout_cwd=w,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"}, db_path=db)
        assert r.get("pass"), r.get("status")
        none_file = w / "none.txt"; none_file.write_text("aaa\nbbb\n", encoding="utf-8")
        hit = K.recall_and_execute_workflow(f"lines containing zzz in {none_file}",
                                            cwd=str(w), db_path=db)
        assert hit is not None
        assert hit["answer"] == []


def test_the_goal_decides_end_to_end_for_a_hash_and_a_count():
    with tempfile.TemporaryDirectory() as td:
        w = pathlib.Path(td)
        s = w / "s.txt"; s.write_text("x\n", encoding="utf-8")
        for name, prog, want_type in (("sha256 of", ["sha256sum"], str),
                                      ("count the lines of", ["wc", "-l"], int)):
            t = w / f"{name.replace(' ', '_')}_t.txt"; t.write_text("a\nb\n", encoding="utf-8")
            h = w / f"{name.replace(' ', '_')}_h.txt"; h.write_text("a\nb\n", encoding="utf-8")
            db = str(w / f"{name.replace(' ', '_')}.sqlite")
            r = K.compile_and_qualify_skill(
                goal=f"{name} {t}",
                trace=[{"kind": "cli_exec", "layer": "cli_exec",
                        "argv": prog + [str(t)]}],
                postcondition=None, heldout_goal=f"{name} {h}", heldout_cwd=w,
                sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                         "contains": "__nope__"}, db_path=db)
            assert r.get("pass"), (name, r.get("status"))
            hit = K.recall_and_execute_workflow(f"{name} {h}", cwd=str(w), db_path=db)
            assert hit is not None
            assert isinstance(hit["answer"], want_type), (name, hit["answer"])
