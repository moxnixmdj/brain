"""r45: the answer gets a TYPE.

THE PROBLEM THIS FIXES
----------------------
Measured in r44: all 23 verbs in the track returned exactly "the number of non-empty lines
the program printed" -- 23 of 23, no exceptions. 'sha256 of <f>' answered 1. 'first column
of <f>' answered 7. The system could not return the lines, the hash, or zero. That was the
bottleneck the 23/33 headline sat on, and it was an ANSWER-TYPE problem, not a learning
problem.

WHAT WAS ADDED
--------------
Postcondition kinds whose answer has a type:
    stdout_lines              -> list[str]  (an empty file answers [])
    stdout_text               -> str        (verbatim)
    stdout_first_token        -> str        (the hash from `sha256sum <f>`)
    stdout_integer_value      -> int        (the INTEGER PRINTED, e.g. `wc -l` -> 4, not 1)
    stdout_line_count_or_zero -> int        (a count where zero is sayable)

`stdout_line_count` is deliberately LEFT ALONE. It must keep failing closed on zero,
because the causal-ablation control used to infer itself from it. See
test_the_ablation_control_no_longer_depends_on_a_failing_check.

MEASURED AFTER
--------------
    'sha256 of <f>'        answer = the 64-char hash  (was: 1)
    'unique lines of <f>'  answer = ['apple','mango','zebra']  (was: 4)
    'count the lines of'   answer = 4, and 0 on an empty file  (was: 1, and 1 on empty)
    'contents of <f>'      answer = the file's text  (was: 7)
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K

FIXTURE = "zebra\napple\nzebra\nmango\n"       # 4 lines, 3 unique


def _er(stdout: str):
    return {"step_receipts": [{"stdout": stdout}]}


# ---------------------------------------------------------------- the types
def test_lines_come_back_as_lines():
    assert K._contract_answer({"kind": "stdout_lines"}, _er("a\nb\n")) == ["a", "b"]


def test_an_empty_file_answers_an_empty_list():
    assert K._contract_answer({"kind": "stdout_lines"}, _er("")) == []


def test_text_comes_back_verbatim():
    assert K._contract_answer({"kind": "stdout_text"}, _er("a\nb\n")) == "a\nb\n"


def test_the_first_token_is_the_hash_not_the_line_count():
    h = "571f95039c5a3c1d8291dc0de1102d365c99dd7b77478a280bf81ed9"
    assert K._contract_answer({"kind": "stdout_first_token"}, _er(h + "  f.txt\n")) == h


def test_the_printed_integer_is_the_answer_not_the_line_count():
    """`wc -l f` prints '4 f' -- ONE line whose integer is 4."""
    assert K._contract_answer({"kind": "stdout_integer_value"}, _er("4 f.txt\n")) == 4
    assert K._contract_answer({"kind": "stdout_integer_value"}, _er("0 empty.txt\n")) == 0


def test_zero_is_sayable_through_the_count_kind():
    assert K._contract_answer({"kind": "stdout_line_count_or_zero"}, _er("")) == 0


# ---------------------------------------------------------------- end to end
def _teach(tmp, name, prog, kind, pre="", slug=None):
    """`slug` keeps filenames free of spaces.

    MEASURED LIMITATION: a path containing a space is tokenised into TWO parameters. The
    goal "count the lines of /tmp/count the lines of_t.txt" produces the skeleton
    "count the lines of ?path0 the lines ?path1" and can never be recalled again. The
    goal language is whitespace-delimited and has no quoting, so a spacey path is
    inexpressible. Not fixed here; pinned by
    test_a_path_with_a_space_is_inexpressible below.
    """
    slug = slug or name.replace(" ", "_")
    t = tmp / f"{slug}_t.txt"; t.write_text(pre or FIXTURE, encoding="utf-8")
    h = tmp / f"{slug}_h.txt"; h.write_text(pre or FIXTURE, encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    db = str(tmp / f"{slug}.sqlite")
    r = K.compile_and_qualify_skill(
        goal=f"{name} {t}",
        trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": prog + [str(t)]}],
        postcondition={"kind": kind},
        heldout_goal=f"{name} {h}", heldout_cwd=tmp,
        sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                 "contains": "__nope__"}, db_path=db)
    assert r.get("pass"), r.get("status")
    return db, h


def test_a_path_with_a_space_is_inexpressible(tmp_path=None):
    """A real, measured limit of the goal language: whitespace-delimited, no quoting."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        t = tmp / "count the lines of_t.txt"; t.write_text(FIXTURE, encoding="utf-8")
        h = tmp / "count the lines of_h.txt"; h.write_text(FIXTURE, encoding="utf-8")
        s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
        db = str(tmp / "sp.sqlite")
        r = K.compile_and_qualify_skill(
            goal=f"count the lines of {t}",
            trace=[{"kind": "cli_exec", "layer": "cli_exec",
                    "argv": ["wc", "-l", str(t)]}],
            postcondition={"kind": "stdout_integer_value"},
            heldout_goal=f"count the lines of {h}", heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"}, db_path=db)
        assert r.get("pass")
        # the space split the path into two parameters
        assert r.get("goal_skeleton", "").count("?path") == 2, r.get("goal_skeleton")
        # It DOES re-match the character-for-character same string (the two parameters
        # happen to bind the right two halves), so the damage is narrower than "unusable":
        # it re-matches only if you ask again with the SAME spacey path. A different
        # spacey path, or a path with a different number of spaces, cannot generalise --
        # the parameter order is fixed at two.
        same = K.recall_and_execute_workflow(f"count the lines of {t}", cwd=str(tmp), db_path=db)
        assert same is not None and same.get("answer") == 4
        other = tmp / "another one.txt"; other.write_text(FIXTURE, encoding="utf-8")
        moved = K.recall_and_execute_workflow(f"count the lines of {other}", cwd=str(tmp),
                                              db_path=db)
        assert moved is None, "a differently-shaped spacey path cannot be matched"


def test_counting_a_file_finally_answers_the_files_line_count():
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        db, h = _teach(tmp, "count the lines of", ["wc", "-l"], "stdout_integer_value")
        hit = K.recall_and_execute_workflow(f"count the lines of {h}", cwd=str(tmp), db_path=db)
        assert hit is not None
        assert hit["answer"] == 4, "4 lines in the file; the old answer was 1"


def test_counting_an_empty_file_answers_zero():
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        # SAME name: the goal skeleton is derived from the goal text, and the db filename
        # is derived from the name, so a different name teaches a different skill.
        db, _ = _teach(tmp, "count the lines of", ["wc", "-l"], "stdout_integer_value")
        empty = tmp / "empty.txt"; empty.write_text("", encoding="utf-8")
        hit = K.recall_and_execute_workflow(f"count the lines of {empty}", cwd=str(tmp),
                                            db_path=db)
        assert hit is not None
        assert hit["answer"] == 0


def test_the_hash_comes_back_instead_of_one():
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        db, h = _teach(tmp, "sha256 of", ["sha256sum"], "stdout_first_token")
        hit = K.recall_and_execute_workflow(f"sha256 of {h}", cwd=str(tmp), db_path=db)
        assert hit is not None
        assert isinstance(hit["answer"], str) and len(hit["answer"]) == 64


# ------------------------------------------- the control must not be inferred
def test_the_ablation_control_no_longer_depends_on_a_failing_check():
    """r44 had to revert `zero verifies` because it silently inverted the ablation control.
    The control now asks the held-out world directly, so a postcondition that CAN verify on
    an empty world no longer breaks qualification."""
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        f = tmp / "a.txt"; f.write_text("MARKER", encoding="utf-8")
        post = {"kind": "file_contains", "path": str(f), "contains": "MARKER"}
        pre = K._heldout_pre_state(post, [], cwd=tmp)
        pre_ok, _ = K.verify_postcondition(post, cwd=tmp, execution_result=pre)
        # the goal already holds: the skill would prove nothing, so ablation must fail
        assert pre_ok is True
        assert (not pre_ok) is False

        g = tmp / "b.txt"; g.write_text("other", encoding="utf-8")
        post2 = {"kind": "file_contains", "path": str(g), "contains": "MARKER"}
        pre2 = K._heldout_pre_state(post2, [], cwd=tmp)
        pre_ok2, _ = K.verify_postcondition(post2, cwd=tmp, execution_result=pre2)
        assert pre_ok2 is False
        assert (not pre_ok2) is True


def test_a_stdout_contract_cannot_hold_before_anything_runs():
    for kind in ("stdout_line_count", "stdout_integer", "stdout_integer_value",
                 "stdout_lines", "stdout_text"):
        post = {"kind": kind}
        pre = K._heldout_pre_state(post, [], cwd=None)
        ok, _ = K.verify_postcondition(post, execution_result=pre)
        assert ok is False, f"{kind} must not hold in a world where nothing ran"
