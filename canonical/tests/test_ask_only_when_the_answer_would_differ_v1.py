"""r62: A TIE IS ONLY A TIE IF THE TWO OPERATIONS ACTUALLY DISAGREE.

Measured before building anything:

    file WITH duplicates    sort -> [a,b,z,z]   sort -u -> [a,b,z]   tie MATTERS
    file with NO duplicates sort -> [a,b,z]     sort -u -> [a,b,z]   tie is EMPTY

Asking in the second case is friction with no information behind it. 2026 counts
over-clarification as a defect in its own right -- the Entity Binding study reports 0.0%
over-clarification across its suite and treats the absence as significant.

So the door now evaluates every tied operation on the real input and compares the answers:

    WITH duplicates     -> ASK, SEVERAL_OPERATIONS_TIE
    NO duplicates       -> ANSWERED, decided_by EXTENSIONAL_EQUIVALENCE
    add duplicates to the same file, ask again -> ASK   (per-call, never cached)

AND IT IS LABELLED. `decided_by: EXTENSIONAL_EQUIVALENCE` with a note saying the choice did
not exist here and this must not be counted as a selection win. A result chosen because both
answers were identical is not evidence that the system understood the question -- it is
evidence that the question had no consequence.

BOUNDED: only carried (read-only) steps are evaluated. A writer cannot be compared by running
it, because comparing it would perform it.
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
    for g, a in [("unique lines of", ["sort", "-u"]), ("sort the lines of", ["sort"])]:
        K.compile_and_qualify_skill(
            goal=f"{g} {t}", trace=[{"kind": "cli_exec", "layer": "cli_exec",
                                     "argv": a + [str(t)]}],
            postcondition=None, heldout_goal=f"{g} {h}", heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"}, db_path=db)
    f = tmp / "no_dupes.txt"; f.write_text("z\na\nb\n", encoding="utf-8")
    return tmp, db, f


def test_when_the_operations_would_agree_it_answers(box):
    tmp, db, f = box
    r = K.answer_or_ask(f"dedupe the lines in {f}", cwd=str(tmp), db_path=db)
    assert r["verdict"] == "ANSWERED"
    assert r["answer"] == ["a", "b", "z"]
    assert r["decided_by"] == "EXTENSIONAL_EQUIVALENCE"
    assert r["compared"] == ["sort ?path0", "sort -u"]


def test_it_says_out_loud_that_this_is_not_a_selection_win(box):
    tmp, db, f = box
    r = K.answer_or_ask(f"dedupe the lines in {f}", cwd=str(tmp), db_path=db)
    assert "must not be counted" in r["note"]


def test_when_the_operations_would_disagree_it_still_asks(box):
    tmp, db, f = box
    f.write_text("z\na\nz\nb\n", encoding="utf-8")
    r = K.answer_or_ask(f"dedupe the lines in {f}", cwd=str(tmp), db_path=db)
    assert r["verdict"] == "ASK"
    assert r["reason"] == "SEVERAL_OPERATIONS_TIE"


def test_the_decision_is_made_per_call_and_never_cached(box):
    """The same file must change the verdict when its contents change. A cached 'they agree'
    would become a false guarantee the moment a duplicate line was appended."""
    tmp, db, f = box
    assert K.answer_or_ask(f"dedupe the lines in {f}", cwd=str(tmp), db_path=db)["verdict"] == "ANSWERED"
    f.write_text("z\na\nz\nb\n", encoding="utf-8")
    assert K.answer_or_ask(f"dedupe the lines in {f}", cwd=str(tmp), db_path=db)["verdict"] == "ASK"


def test_the_comparison_only_runs_carried_read_only_steps(box):
    """A writer cannot be compared by running it, because comparing it would perform it."""
    from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K2
    steps = [{"layer": "cli_exec", "argv": ["rm", "?path0"]}]
    assert K2._steps_are_all_carried(steps) is False


def test_equivalence_returns_none_rather_than_guessing_when_anything_fails(box):
    tmp, db, f = box
    # no such file: every tied proposal fails, so the comparison must decline
    assert K.answer_by_equivalence(f"dedupe the lines in {tmp/'missing.txt'}",
                                   cwd=str(tmp), db_path=db) is None
