"""r60: IF A MODEL IS ATTACHED, ITS JOB IS TO PICK -- AND THE SUBSTRATE CAN CATCH IT.

The goal is "literally anything on a computer" plus advanced software engineering. The
first missing part is a model (r56 rank 1). The question that decides whether attaching one
is safe is not "how good is the model" but "what happens when it picks wrong".

MEASURED. Four proposals handed to the existing contract-and-shape validator:

    correct  sort -u   for "unique lines of"   -> SHAPE_MATCHES_THE_GOAL
    WRONG    wc -l     for "unique lines of"   -> SHAPE_MISMATCH__GOAL_ASKED_FOR_A_DIFFERENT_KIND
    WRONG    cat       for "sha256 of"         -> SHAPE_MISMATCH__GOAL_ASKED_FOR_A_DIFFERENT_KIND
    WRONG    sort -u   for "count the lines of"-> SHAPE_MISMATCH__GOAL_ASKED_FOR_A_DIFFERENT_KIND

3 of 3 type-changing wrong picks caught. The hole is exact and known: a wrong pick between
two operations that return the SAME KIND of answer (`sort` vs `sort -u`, both lines) passes.
That is r52's defect and the shape audit was never able to see it.

This is not a new architecture. ToolGate (Findings of ACL 2026) formalises it the same way:
tools carry Hoare-style pre/postconditions, the precondition gates invocation, the
postcondition decides whether the result may be committed to state, and "the symbolic state
evolves only through verified tool executions, preventing invalid or hallucinated results
from corrupting the world representation." Its reported failure distribution is also the
argument for keeping the gate: parametric hallucination is the most prevalent error at 8.4%.

The value of this repository to that architecture is not a better model. It is that the gate
already exists, is executable, and can be measured.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K

TEACH = {"sort -u": ("unique lines of", ["sort", "-u"]),
         "sort": ("sort the lines of", ["sort"]),
         "wc -l": ("count the lines of", ["wc", "-l"]),
         "cat": ("dump the contents of", ["cat"]),
         "sha256sum": ("sha256 of", ["sha256sum"])}


@pytest.fixture(scope="module")
def box():
    tmp = pathlib.Path(tempfile.mkdtemp())
    db = str(tmp / "s.sqlite")
    t = tmp / "teach.txt"; t.write_text("z\na\nz\nb\n", encoding="utf-8")
    h = tmp / "hold.txt"; h.write_text("m\nn\nm\n", encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    ids = {}
    for sig, (g, a) in TEACH.items():
        r = K.compile_and_qualify_skill(
            goal=f"{g} {t}", trace=[{"kind": "cli_exec", "layer": "cli_exec",
                                     "argv": a + [str(t)]}],
            postcondition=None, heldout_goal=f"{g} {h}", heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"}, db_path=db)
        ids[sig] = r["skill_id"]
    f = tmp / "data.txt"; f.write_text("z\na\nz\nb\n", encoding="utf-8")
    rows = {r["skill_id"]: r for r in K._load_cached_skills(db_path=db)}
    return tmp, f, ids, rows


def _propose(box, goal, sig):
    tmp, f, ids, rows = box
    sk = rows[ids[sig]]
    steps = K._instantiate_obj(sk["abstract_steps"], {"?path0": str(f)})
    res = K.execute_compiled_steps(steps, cwd=str(tmp))
    ok, why = K.verify_postcondition(sk.get("abstract_postcondition"), cwd=str(tmp),
                                     execution_result=res)
    ans = K._contract_answer(sk.get("abstract_postcondition"), res)
    return ok, ans, K.audit_answer_shape(goal, {"answer": ans})


@pytest.mark.parametrize("goal_head,sig,expected", [
    ("unique lines of", "wc -l", False),
    ("sha256 of", "cat", False),
    ("count the lines of", "sort -u", False),
])
def test_a_type_changing_wrong_pick_is_caught(box, goal_head, sig, expected):
    tmp, f, _, _ = box
    ok, ans, shape = _propose(box, f"{goal_head} {f}", sig)
    assert ok, "the wrong skill still executes cleanly -- that is why the gate is needed"
    assert shape["shape_matches"] is expected
    assert shape["verdict"].startswith("SHAPE_MISMATCH")


def test_a_correct_pick_passes_the_gate(box):
    tmp, f, _, _ = box
    ok, ans, shape = _propose(box, f"unique lines of {f}", "sort -u")
    assert ok and ans == ["a", "b", "z"]
    assert shape["shape_matches"] is True


def test_the_hole_is_a_wrong_pick_of_the_SAME_answer_kind(box):
    """`sort` for 'unique lines of' returns lines, so the shape audit is satisfied. This is
    the one error the substrate cannot catch and the reason a model cannot be trusted alone."""
    tmp, f, _, _ = box
    ok, ans, shape = _propose(box, f"unique lines of {f}", "sort")
    assert ok
    assert ans == ["a", "b", "z", "z"], "sorted, duplicates kept -- not deduped"
    assert shape["shape_matches"] is True, "the gate passes it: same kind, different operation"


def test_the_gate_does_not_need_a_model_to_be_measured(box):
    """0 parameters. The catch rate is a property of the contract layer, so it is
    reproducible without any model attached."""
    tmp, f, _, _ = box
    caught = 0
    for head, sig in [("unique lines of", "wc -l"), ("sha256 of", "cat"),
                      ("count the lines of", "sort -u")]:
        _, _, shape = _propose(box, f"{head} {f}", sig)
        if shape["shape_matches"] is False:
            caught += 1
    assert caught == 3
