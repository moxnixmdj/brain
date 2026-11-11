"""r58: ASK ONCE, LEARN THE DEFAULT, NEVER ASK AGAIN -- AND CARRY IT TO A NEW FILE.

This is the one part of the standing thesis that survives measurement intact.

r55-r57 made the system refuse a tie and raise it as a question. Correct, and on its own a
regression in usefulness: a user who says "dedupe the lines in" twice gets asked twice,
having answered once. The missing piece was a table keyed by the PHRASE rather than by the
document.

Measured:

    first ask, tied            -> ASK
    user answers "the unique-lines one"
    second ask, same file      -> ANSWERED, and the answer says which clarification it used
    third ask, DIFFERENT file  -> ANSWERED, ['a', 'b']

2026 does this too, and the phrasing is specific: "the conversation does not carry the
clarification across turns; the LEARNED DEFAULT carries it across requests" (When RAG Users
Ask Vague Questions, 2026). ReferClaw (arXiv 2611.07683) and PAHF (arXiv 2602.16173) both
learn intent-specific skills from verified clarification feedback.

WHERE THIS DELIBERATELY DIVERGES. Those systems learn a default for a missing FIELD (which
document, which page) and apply it silently once confident. This learns which of several
TAUGHT OPERATIONS a repeated PHRASE means. It holds no confidence band and applies no
threshold: one answer to one question, applied to that phrasing and no other. A remembered
choice that turns out to be wrong fails loudly, because the carrier still executes it and
the postcondition still verifies it -- the memory decides WHICH skill, never whether it
worked.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K


@pytest.fixture()
def box():
    tmp = pathlib.Path(tempfile.mkdtemp())
    db = str(tmp / "s.sqlite")
    t = tmp / "teach.txt"; t.write_text("z\na\nz\n", encoding="utf-8")
    h = tmp / "hold.txt"; h.write_text("m\nn\nm\n", encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    ids = {}
    for g, a in [("unique lines of", ["sort", "-u"]), ("count the lines of", ["wc", "-l"])]:
        r = K.compile_and_qualify_skill(
            goal=f"{g} {t}",
            trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": a + [str(t)]}],
            postcondition=None, heldout_goal=f"{g} {h}", heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"}, db_path=db)
        ids[a[0]] = r["skill_id"]
    f1 = tmp / "data.txt"; f1.write_text("z\nq\nz\n", encoding="utf-8")
    f2 = tmp / "other.log"; f2.write_text("b\na\nb\n", encoding="utf-8")
    return tmp, db, f1, f2, ids


def test_the_first_ask_is_a_question(box):
    tmp, db, f1, _, _ = box
    assert K.answer_or_ask(f"dedupe the lines in {f1}", cwd=str(tmp), db_path=db)["verdict"] == "ASK"


def test_after_one_answer_the_same_phrase_is_answered(box):
    tmp, db, f1, _, ids = box
    K.remember_clarification(f"dedupe the lines in {f1}", ids["sort"], db_path=db)
    r = K.answer_or_ask(f"dedupe the lines in {f1}", cwd=str(tmp), db_path=db)
    assert r["verdict"] == "ANSWERED"
    assert r["answer"] == ["q", "z"]
    assert r["learned_from_clarification"]["operation"] == "sort -u"


def test_the_learned_choice_carries_to_a_different_file(box):
    """The key drops the operand, so the same phrasing about a new file is the same question."""
    tmp, db, f1, f2, ids = box
    K.remember_clarification(f"dedupe the lines in {f1}", ids["sort"], db_path=db)
    r = K.answer_or_ask(f"dedupe the lines in {f2}", cwd=str(tmp), db_path=db)
    assert r["verdict"] == "ANSWERED"
    assert r["answer"] == ["a", "b"]


def test_the_learned_choice_is_scoped_to_the_phrase(box):
    """A different phrasing is a different question. Memory must not leak across asks."""
    tmp, db, f1, f2, ids = box
    K.remember_clarification(f"dedupe the lines in {f1}", ids["sort"], db_path=db)
    r = K.answer_or_ask(f"how many lines are in {f2}", cwd=str(tmp), db_path=db)
    assert r.get("learned_from_clarification") is None


def test_a_wrong_remembered_choice_fails_loudly_not_quietly(box):
    """The memory decides WHICH skill. The carrier and the postcondition still decide whether
    it worked, so a remembered answer that cannot verify does not become an answer."""
    tmp, db, f1, _, _ = box
    K.remember_clarification(f"dedupe the lines in {f1}", "workflow.invented", db_path=db)
    r = K.answer_or_ask(f"dedupe the lines in {f1}", cwd=str(tmp), db_path=db)
    assert r["verdict"] == "ASK", "an unusable memory row must fall back to asking"


def test_an_unusable_skill_id_is_rejected_at_write_time(box):
    _, db, f1, _, _ = box
    r = K.remember_clarification(f"dedupe the lines in {f1}", "workflow.invented", db_path=db)
    assert r["stored"] is False and r["reason"] == "NO_SUCH_SKILL"
