"""r44: the answer a skill returns is the LINE COUNT OF ITS OWN OUTPUT.

THE MEASUREMENT
---------------
All 23 verbs in the r41 track qualify and recall. Every one of them returns the number of
non-empty lines the program printed. That is true 23 of 23 times, exactly.

Why it matters: `stdout_line_count` was chosen because "how many unique lines" is a
natural question. But it answers "how many lines did you print", which for a set-valued
program (`sort -u`, `grep`) is a decent proxy and for everything else is not the goal.

    goal stored                        answer   what it means
    unique lines of <f>                   4     correct -- 4 unique lines printed
    count the lines of <f>                1     `wc -l` prints ONE line; the file's count
                                                 (7) is inside it as text, never parsed
    sha256 of <f>                         1     a hash was printed; the answer is "1"
    contents of <f>                       7     `cat` printed 7 lines
    first column of <f>                   7     7 one-character columns

So the 23/33 headline is a reproducibility measurement -- "the same command runs and prints
something on a new file" -- not a correctness measurement against each goal. Both are real;
they are not the same claim, and this test keeps them apart.

THE BUG FOUND WHILE MEASURING THIS
----------------------------------
An EMPTY file answered 1 with pass=True. `wc -l` prints "0 empty.txt" -- one line -- so the
verifier reported 1. The correct answer (0) is unreachable: `stdout_line_count` fails
closed on zero.

Making zero pass was tried and REVERTED, because `causal_ablation_pass = not pre_ok`
requires an empty postcondition check to FAIL before the skill runs. Allowing 0 to verify
silently inverts the causal ablation control and the ownership gate then rejects every
skill ("REQUIRED_TRUE_MISSING:causal_ablation_pass"). The limit stands, named, below.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K

FIXTURE = "zebra\napple\nzebra\nmango\napple\nkiwi\nmango\n"   # 7 lines, 4 unique


def _teach_and_ask(verb_argv, goal, tmp):
    t = tmp / "t.txt"; t.write_text(FIXTURE, encoding="utf-8")
    h = tmp / "h.txt"; h.write_text(FIXTURE, encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    db = str(tmp / "skills.sqlite")
    r = K.compile_and_qualify_skill(
        goal=f"{goal} {t}",
        trace=[{"kind": "cli_exec", "layer": "cli_exec",
                "argv": [verb_argv[0], *verb_argv[1:], str(t)]}],
        postcondition={"kind": "stdout_line_count"},
        heldout_goal=f"{goal} {h}", heldout_cwd=tmp,
        sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                 "contains": "__nope__"},
        db_path=db,
    )
    assert r.get("pass"), r.get("status")
    hit = K.recall_and_execute_workflow(f"{goal} {h}", cwd=str(tmp), db_path=db)
    assert hit is not None
    return hit.get("answer")


def test_the_answer_is_the_count_of_lines_printed_not_the_good_answer():
    """`wc -l` on a 7-line file. The right answer is 7; the skill says 1, and both the
    skill and the postcondition agree -- because the postcondition was never asking."""
    with tempfile.TemporaryDirectory() as td:
        assert _teach_and_ask(["wc", "-l"], "count the lines of",
                              pathlib.Path(td)) == 1


def test_a_set_valued_program_gives_the_useful_number_by_luck_of_shape():
    """`sort -u` prints one line per unique line, so 'lines printed' == 'unique lines'."""
    with tempfile.TemporaryDirectory() as td:
        assert _teach_and_ask(["sort", "-u"], "unique lines of",
                              pathlib.Path(td)) == 4


def test_an_empty_file_cannot_be_answered_at_all():
    """Truth is 0. The system will say 1 (`wc -l` prints one line: '0 <file>')."""
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        db = str(tmp / "skills.sqlite")
        t = tmp / "t.txt"; t.write_text(FIXTURE, encoding="utf-8")
        h = tmp / "h.txt"; h.write_text(FIXTURE, encoding="utf-8")
        s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
        r = K.compile_and_qualify_skill(
            goal=f"count the lines of {t}",
            trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": ["wc", "-l", str(t)]}],
            postcondition={"kind": "stdout_line_count"},
            heldout_goal=f"count the lines of {h}", heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"}, db_path=db)
        assert r.get("pass")
        empty = tmp / "empty.txt"; empty.write_text("", encoding="utf-8")
        hit = K.recall_and_execute_workflow(f"count the lines of {empty}",
                                            cwd=str(tmp), db_path=db)
        # truth is 0; the system asserts 1 and calls it verified
        assert hit is not None
        assert hit.get("answer") == 1


def test_zero_cannot_verify_and_must_not_be_made_to():
    """This pins the reason the obvious fix is wrong. If someone 'fixes' the zero case,
    the causal ablation control inverts and EVERY skill is refused. That is a far worse
    failure than being unable to say 'zero', so the check must keep failing on empty."""
    ok, why = K.verify_postcondition({"kind": "stdout_line_count"}, execution_result={})
    assert ok is False
    assert why == "POSTCONDITION_STDOUT_LINE_COUNT_ZERO"
