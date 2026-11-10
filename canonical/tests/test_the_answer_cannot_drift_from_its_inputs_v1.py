"""r49: snapshot the input, and audit the SHAPE as well as the derivation.

r48's stated limit was that its audit re-ran commands against the CURRENT filesystem --
re-derivation, not replay. Measured here: edit the file after answering and the old audit
silently flipped to ANSWER_NOT_DERIVABLE, blaming the skill for the auditor's own staleness.
Now the inputs are hashed at answer time and a changed input makes the audit refuse to speak.

r48's other stated limit was that every audit answers "is the answer derivable from the argv
it claims" and never "is that argv the right thing to run". Demonstrated, not assumed: a
skill whose goal says "count the lines" was made to hold `sort -u`; asked for a count it
returned ['apple','zebra'] and the derivation audit said ANSWER_MATCHES_ITS_SOURCE. A second
layer now compares the goal's requested TYPE against the answer's actual type and catches it.

WHAT IS STILL OPEN, stated plainly: a wrong answer of the CORRECT type passes both layers.
"count the unique lines" against a goal of "count the lines" is an integer either way, and
no deterministic comparator can tell.
"""
from __future__ import annotations

import pathlib
import sqlite3
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K

ALPHA = "zebra\napple\nzebra\n"
HELD = "one\ntwo\none\n"


@pytest.fixture()
def recalled():
    tmp = pathlib.Path(tempfile.mkdtemp())
    db = str(tmp / "a.sqlite")
    a = tmp / "alpha.txt"; a.write_text(ALPHA, encoding="utf-8")
    h = tmp / "held.txt"; h.write_text(HELD, encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    r = K.compile_and_qualify_skill(
        goal=f"unique lines of {a}",
        trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": ["sort", "-u", str(a)]}],
        postcondition=None, heldout_goal=f"unique lines of {h}", heldout_cwd=tmp,
        sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                 "contains": "__nope__"}, db_path=db)
    assert r.get("pass"), r.get("status")
    hit = K.recall_and_execute_workflow(f"unique lines of {a}", cwd=str(tmp), db_path=db)
    assert hit is not None
    return hit, a, tmp, db


# ------------------------------------------------------------- input snapshot
def test_the_answer_records_the_bytes_it_read(recalled):
    hit, a, tmp, db = recalled
    inputs = hit["provenance"]["inputs"]
    assert len(inputs) == 1
    assert inputs[0]["path"].endswith("alpha.txt")
    assert len(inputs[0]["sha256"]) == 64
    assert inputs[0]["bytes"] == len(ALPHA)


def test_editing_the_input_afterwards_makes_the_audit_refuse_to_speak(recalled):
    """r48 would have said ANSWER_NOT_DERIVABLE here and blamed the skill."""
    hit, a, tmp, db = recalled
    assert K.audit_answer_by_rederivation(hit)["verdict"] == "ANSWER_MATCHES_ITS_SOURCE"
    a.write_text("totally\ndifferent\nnow\n", encoding="utf-8")
    audit = K.audit_answer_by_rederivation(hit)
    assert audit["auditable"] is False
    assert audit["verdict"] == "NOT_AUDITABLE__INPUTS_CHANGED_SINCE_THE_ANSWER"
    assert audit["drift"][0]["change"] == "CONTENT_CHANGED"
    assert audit["drift"][0]["was_sha256"] != audit["drift"][0]["now_sha256"]


def test_deleting_the_input_is_also_drift_not_a_verdict(recalled):
    hit, a, tmp, db = recalled
    a.unlink()
    audit = K.audit_answer_by_rederivation(hit)
    assert audit["verdict"] == "NOT_AUDITABLE__INPUTS_CHANGED_SINCE_THE_ANSWER"
    assert audit["drift"][0]["change"] == "GONE"


# ---------------------------------------------------------------- shape audit
def test_an_honest_answer_has_the_shape_the_goal_asked_for(recalled):
    hit, a, tmp, db = recalled
    assert hit["shape_audit"]["verdict"] == "SHAPE_MATCHES_THE_GOAL"


def test_a_skill_answering_the_wrong_kind_of_question_is_caught(recalled):
    """The r48 hole, made concrete: goal says 'count', argv is `sort -u`."""
    hit, a, tmp, db = recalled
    conn = sqlite3.connect(db)
    conn.execute(
        "UPDATE compiled_workflow_skills SET goal_skeleton=?, goal_regex=?",
        ("count the lines of ?path0",
         r"^\s*count\s+the\s+lines\s+of\s+(?P<path0>[^\s\"',;)]+?)\.?\s*$"))
    conn.commit(); conn.close()

    wrong = K.recall_and_execute_workflow(f"count the lines of {a}", cwd=str(tmp), db_path=db)
    assert wrong is not None
    assert isinstance(wrong["answer"], list), "sort -u returns lines, not a count"
    # the derivation audit is satisfied -- and that is exactly the hole
    assert K.audit_answer_by_rederivation(wrong)["verdict"] == "ANSWER_MATCHES_ITS_SOURCE"
    # the shape audit is not
    assert wrong["shape_audit"]["verdict"] == "SHAPE_MISMATCH__GOAL_ASKED_FOR_A_DIFFERENT_KIND"
    assert wrong["shape_audit"]["goal_requested_type"] == "stdout_integer_value"
    assert wrong["shape_audit"]["answer_actual_type"] == "stdout_lines"


def test_the_shape_audit_admits_what_it_cannot_do():
    audit = K.audit_answer_shape("count the lines of f", {"answer": 3})
    assert "a shape check only" in audit["honesty"]
    assert "CHOICE" in audit["honesty"]


def test_a_wrong_answer_of_the_right_type_passes_both_layers():
    """The permanent hole, pinned so nobody claims it was closed."""
    shape = K.audit_answer_shape("count the lines of f", {"answer": 999})
    assert shape["verdict"] == "SHAPE_MATCHES_THE_GOAL"
