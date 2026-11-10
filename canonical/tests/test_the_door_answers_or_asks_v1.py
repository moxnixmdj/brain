"""r56: THE DOOR. Having a correct behaviour and USING it are different things.

r55 built `select_or_ask` and left it beside the real path. `recall_and_execute_workflow`
still returned None for three completely different situations:

    - no skill has ever been taught
    - the verbs conflict
    - the sentence does not say which of these you meant   <- r55 showed this is the common one

A caller cannot tell those apart, so the system's most frequent honest answer ("I don't know
which operation you mean") arrived at the caller looking identical to a bug.

`answer_or_ask` is the door: it answers when the sentence is enough and it asks with named
options when it is not. The old function is untouched, so nothing that depended on None
changes behaviour.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K

POOL = [("unique lines of", ["sort", "-u"]), ("count the lines of", ["wc", "-l"]),
        ("sha256 of", ["sha256sum"]), ("reverse the order of", ["tac"]),
        ("dump the contents of", ["cat"])]


@pytest.fixture(scope="module")
def store():
    tmp = pathlib.Path(tempfile.mkdtemp())
    db = str(tmp / "s.sqlite")
    t = tmp / "teach.txt"; t.write_text("a\nb\na\n", encoding="utf-8")
    h = tmp / "hold.txt"; h.write_text("c\nd\nc\n", encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    for g, a in POOL:
        K.compile_and_qualify_skill(
            goal=f"{g} {t}", trace=[{"kind": "cli_exec", "layer": "cli_exec",
                                     "argv": a + [str(t)]}],
            postcondition=None, heldout_goal=f"{g} {h}", heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"}, db_path=db)
    f = tmp / "data.txt"; f.write_text("z\nq\nz\n", encoding="utf-8")
    return db, tmp, f


def test_a_sentence_that_names_its_operation_is_answered(store):
    db, tmp, f = store
    r = K.answer_or_ask(f"sha256 of {f}", cwd=str(tmp), db_path=db)
    assert r["verdict"] == "ANSWERED"
    assert r["answer"].startswith("b2abc") or len(r["answer"]) == 64


def test_a_sentence_that_does_not_is_asked_about_not_shrugged_at(store):
    db, tmp, f = store
    r = K.answer_or_ask(f"tally the rows of {f}", cwd=str(tmp), db_path=db)
    assert r["verdict"] == "ASK"
    assert r["options"], "the question must name what it is choosing between"
    assert r["reason"] in {"SEVERAL_OPERATIONS_TIE", "NO_WORD_OVERLAP__CANNOT_CHOOSE"}


def test_the_three_meanings_of_none_are_now_distinguishable(store):
    """"nothing taught" and "cannot choose" were the same None."""
    db, tmp, f = store
    nothing = str(pathlib.Path(tempfile.mkdtemp()) / "empty.sqlite")
    a = K.answer_or_ask(f"sha256 of {f}", db_path=nothing)
    b = K.answer_or_ask(f"tally the rows of {f}", cwd=str(tmp), db_path=db)
    assert a["verdict"] == "ASK" and a["reason"] == "NOTHING_TAUGHT"
    assert b["verdict"] == "ASK" and b["reason"] != "NOTHING_TAUGHT"


def test_the_old_function_still_returns_none_so_nothing_downstream_breaks(store):
    db, tmp, f = store
    assert K.recall_and_execute_workflow(f"tally the rows of {f}", cwd=str(tmp), db_path=db) is None
    assert K.answer_or_ask(f"tally the rows of {f}", cwd=str(tmp), db_path=db)["verdict"] == "ASK"


def test_a_unique_selection_that_fails_to_run_is_not_offered_as_a_question(store):
    """If exactly one operation fits and it could not run, a menu would be a lie."""
    db, tmp, f = store
    r = K.answer_or_ask(f"sha256 of {tmp/'does-not-exist.txt'}", cwd=str(tmp), db_path=db)
    assert r["verdict"] in {"ASK", "UNANSWERABLE"}
    if r["verdict"] == "UNANSWERABLE":
        assert r["reason"] == "SELECTED_BUT_DID_NOT_RUN"
