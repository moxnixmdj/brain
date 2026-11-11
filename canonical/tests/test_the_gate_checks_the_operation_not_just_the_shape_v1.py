"""r61: RANK 2 OF THE PATH -- WIDEN THE GATE FROM KIND TO OPERATION.

Measured on the real record before the fix:

    taught 'sort -u'    postcondition = {'kind': 'stdout_lines'}
    taught 'sort'       postcondition = {'kind': 'stdout_lines'}

Identical. The postcondition describes how to check the OUTPUT SHAPE and says nothing about
which operation produced it, so "unique lines of" answered by plain `sort` verified and
returned the duplicates it was asked to remove. r60 measured 3/3 type-changing wrong picks
caught and named this as the one it could not see.

AFTER. The gate reads the goal for a verifiable commitment and checks the argv that ran:

    proposal: sort for "unique lines of"
      postcondition check : True  STDOUT_LINES_VERIFIED:4
      shape audit         : SHAPE_MATCHES_THE_GOAL      <- r60 could not catch this
      commitment gate     : False OPERATION_NOT_HONOURED__ASKED_FOR_-u

The correct proposal still passes: OPERATION_COMMITTED:-u.

HONEST LIMIT. This closes one family: dedupe / unique / distinct -> `-u`. A goal naming no
verifiable flag gets no extra protection, deliberately -- a gate that fires on wording it
cannot verify rejects correct answers, and r53 already paid for that mistake once.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K


@pytest.fixture(scope="module")
def box():
    tmp = pathlib.Path(tempfile.mkdtemp())
    db = str(tmp / "s.sqlite")
    t = tmp / "teach.txt"; t.write_text("z\na\nz\nb\n", encoding="utf-8")
    h = tmp / "hold.txt"; h.write_text("m\nn\nm\n", encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    ids = {}
    for sig, (g, a) in {"sort -u": ("unique lines of", ["sort", "-u"]),
                        "sort": ("sort the lines of", ["sort"]),
                        "wc -l": ("count the lines of", ["wc", "-l"])}.items():
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


def _run(box, sig):
    tmp, f, ids, rows = box
    sk = rows[ids[sig]]
    return K.execute_compiled_steps(
        K._instantiate_obj(sk["abstract_steps"], {"?path0": str(f)}), cwd=str(tmp))


def test_the_two_operations_carry_identical_postconditions(box):
    """The defect, stated as a fact about the stored records."""
    _, _, ids, rows = box
    a = rows[ids["sort -u"]].get("abstract_postcondition")
    b = rows[ids["sort"]].get("abstract_postcondition")
    assert a == b == {"kind": "stdout_lines"}


def test_a_wrong_pick_of_the_same_kind_is_now_caught(box):
    _, f, _, _ = box
    res = _run(box, "sort")
    commit = K.infer_operation_commitment(f"unique lines of {f}")
    ok, reason = K.verify_operation_commitment(commit, res)
    assert ok is False
    assert reason == "OPERATION_NOT_HONOURED__ASKED_FOR_-u"


def test_the_correct_pick_still_passes(box):
    _, f, _, _ = box
    res = _run(box, "sort -u")
    ok, reason = K.verify_operation_commitment(K.infer_operation_commitment(f"unique lines of {f}"), res)
    assert ok is True and reason == "OPERATION_COMMITTED:-u"


@pytest.mark.parametrize("phrasing", ["unique lines of", "distinct lines of", "dedupe the lines in"])
def test_the_commitment_reads_the_goal_not_the_answer(phrasing):
    assert K.infer_operation_commitment(f"{phrasing} data.txt") == ("contains", "-u")


def test_a_goal_with_no_verifiable_flag_adds_no_check():
    """Deliberate narrowness. This gate must not fire where it cannot verify, or it becomes
    the r53 mistake: a refusal that rejects correct answers."""
    for g in ("count the lines of data.txt", "show me the content of data.txt",
              "sha256 of data.txt"):
        assert K.infer_operation_commitment(g) is None


def test_no_execution_means_unverifiable_not_passed():
    ok, reason = K.verify_operation_commitment(("contains", "-u"), None)
    assert ok is False and reason == "OPERATION_COMMITMENT_UNVERIFIABLE__NO_EXECUTION"
