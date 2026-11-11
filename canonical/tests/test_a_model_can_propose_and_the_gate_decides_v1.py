"""r63: THE MODEL WAS NEVER MISSING. IT HAD NO SOCKET.

Twenty-nine rounds reported "rank 1: there is no model, 0 parameters" as the binding
constraint. That was true about the files and false about the system: every round was written
by a language model that read the goals and chose the code. The model was in the loop from
round 34. It was never given a place to put its choice.

`model_proposes_v1` is that place. An LLM reads (goal, catalog) and writes an artifact of
proposals; the module loads the artifact and hands each proposal to the gates that already
exist. The proposal is a FILE on purpose: a model whose choices are not recorded cannot be
held to them.

MEASURED, with the model being this session's author, choosing blind from the catalog alone
and recording confidence before anything ran:

    8/8 answered, 0 gate refusals      (against 4/8 for the lexical selector in r50)

That is the ceiling from r55 collapsing, exactly as predicted, and no new mechanism was
needed to collapse it.

THE PART THAT MATTERS MORE: deliberately bad proposals.

    sort (no -u) for "dedupe the lines in"   -> REFUSED  OPERATION_NOT_HONOURED
    cat for "sha256 of"                      -> REFUSED  ANSWER_SHAPE_DOES_NOT_MATCH_THE_GOAL
    sort -u for "how many lines are in"      -> REFUSED  ANSWER_SHAPE_DOES_NOT_MATCH_THE_GOAL
    a skill_id not in the catalog            -> REFUSED  PROPOSED_SKILL_NOT_IN_THE_CATALOG

4/4 refused. The first two refusals in that list were NOT working when this round started:
the model-proposes path skipped the r49 shape audit, because until now nothing could propose
a skill that the question had not also selected. Writing a hostile proposal found it; reading
the code did not.
"""
from __future__ import annotations

import json
import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K
from canonical.swe_kernel import model_proposes_v1 as M

POOL = [("unique lines of", ["sort", "-u"]), ("count the lines of", ["wc", "-l"]),
        ("sha256 of", ["sha256sum"]), ("dump the contents of", ["cat"]),
        ("reverse each line of", ["rev"]), ("reverse the order of", ["tac"]),
        ("first line of", ["head", "-1"]), ("sort the lines of", ["sort"])]


@pytest.fixture(scope="module")
def box():
    tmp = pathlib.Path(tempfile.mkdtemp())
    db = str(tmp / "s.sqlite")
    t = tmp / "teach.txt"; t.write_text("z\na\nz\nb\n", encoding="utf-8")
    h = tmp / "hold.txt"; h.write_text("m\nn\nm\n", encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    ids = {}
    for g, a in POOL:
        r = K.compile_and_qualify_skill(
            goal=f"{g} {t}", trace=[{"kind": "cli_exec", "layer": "cli_exec",
                                     "argv": a + [str(t)]}],
            postcondition=None, heldout_goal=f"{g} {h}", heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"}, db_path=db)
        ids[" ".join(a[:2])] = r["skill_id"]
    f = tmp / "data.txt"; f.write_text("z\na\nz\nb\n", encoding="utf-8")
    return tmp, pathlib.Path(db), f, ids


def _prop(sid, conf=0.9):
    return {"skill_id": sid, "confidence": conf, "because": "test"}


def test_the_model_choosing_blind_answers_eight_of_eight(box):
    """The real artifact, not a fixture: it is the file this session's author wrote from the
    catalog alone, with confidences recorded before the gate ran."""
    tmp, db, f, _ = box
    path = pathlib.Path(__file__).resolve().parents[1] / "evaluation" / "model_in_the_loop" / "proposals_20261109_v1.json"
    props = M.load_proposals(path)
    answered = sum(1 for ask, p in props.items()
                   if M.answer_from_proposal(f"{ask} {f}", p, cwd=str(tmp), db_path=db)["verdict"] == "ANSWERED")
    assert answered == 8


def test_the_gate_refuses_a_wrong_operation_of_the_same_kind(box):
    tmp, db, f, ids = box
    r = M.answer_from_proposal(f"dedupe the lines in {f}", _prop(ids["sort"]), cwd=str(tmp), db_path=db)
    assert r["verdict"] == "REFUSED_BY_GATE"
    assert "OPERATION_NOT_HONOURED" in r["reason"]


def test_the_gate_refuses_an_answer_of_the_wrong_shape(box):
    """The hole this round found by writing a hostile proposal: the model-proposes path was
    skipping the r49 shape audit entirely."""
    tmp, db, f, ids = box
    r = M.answer_from_proposal(f"sha256 of {f}", _prop(ids["cat"]), cwd=str(tmp), db_path=db)
    assert r["verdict"] == "REFUSED_BY_GATE"
    assert "ANSWER_SHAPE_DOES_NOT_MATCH_THE_GOAL" in r["reason"]
    assert "would_have_said" in r, "the refusal must show what it would have returned"


def test_the_gate_refuses_a_counting_question_answered_with_a_listing(box):
    tmp, db, f, ids = box
    r = M.answer_from_proposal(f"how many lines are in {f}", _prop(ids["sort -u"]), cwd=str(tmp), db_path=db)
    assert r["verdict"] == "REFUSED_BY_GATE"


def test_the_gate_refuses_a_skill_that_is_not_in_the_catalog(box):
    tmp, db, f, _ = box
    r = M.answer_from_proposal(f"sha256 of {f}", _prop("workflow.does-not-exist"),
                               cwd=str(tmp), db_path=db)
    assert r["verdict"] == "REFUSED_BY_GATE"
    assert r["reason"] == "PROPOSED_SKILL_NOT_IN_THE_CATALOG"


def test_an_abstention_is_honoured_as_an_ask(box):
    """A model that declines is behaving correctly under r55's ceiling, and the substrate
    must not punish it or override it."""
    tmp, db, f, _ = box
    r = M.answer_from_proposal(f"backwards {f}", {"skill_id": "ABSTAIN"}, cwd=str(tmp), db_path=db)
    assert r["verdict"] == "ASK"


def test_no_proposal_is_not_an_answer(box):
    tmp, db, f, _ = box
    assert M.answer_from_proposal(f"sha256 of {f}", None, cwd=str(tmp), db_path=db)["verdict"] == "NO_PROPOSAL"


def test_confidence_is_recorded_but_is_never_a_licence(box):
    """A 0.99 on a wrong choice is refused exactly like a 0.01. Confidence is evidence for an
    auditor afterwards; it is not a credential."""
    tmp, db, f, ids = box
    for conf in (0.01, 0.5, 0.99, 1.0):
        r = M.answer_from_proposal(f"sha256 of {f}", _prop(ids["cat"], conf=conf),
                                   cwd=str(tmp), db_path=db)
        assert r["verdict"] == "REFUSED_BY_GATE", conf
