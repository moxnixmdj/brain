"""r54: TWO STEPS ARE NOT A PIPELINE, AND BOTH OF THEM SAY PASS.

THE DEFECT. A skill recorded as

    step 0: sort -u <file>
    step 1: wc -l

compiles (PASS__WORKFLOW_SKILL_COMPILED_QUALIFIED_AND_OWNED), recalls, executes both
steps, and returns **0**. The truth is 3. It reports `pass: true`,
`STDOUT_INTEGER_VERIFIED:0`, and the shape audit says SHAPE_MATCHES_THE_GOAL.

The cause is not a bug in either step. It is that `cli_exec` steps are executed
independently, each with `stdin=subprocess.DEVNULL`. Step 0 writes `a\nb\nz\n` to its own
receipt and exits. Step 1 is then run on its own with no stdin, `wc -l` gets EOF and prints
`0`, and exits 0 because that is what wc does with empty input.

The same skill taught as ONE `cli_pipeline` step answers 3. Both compile. Both pass.

WHY THIS IS THE WORST THING FOUND IN NINETEEN ROUNDS. The wrong answer and the right one
are indistinguishable to every instrument in this project:

    real empty file   -> answer 0, STDOUT_INTEGER_VERIFIED:0
    broken pipeline   -> answer 0, STDOUT_INTEGER_VERIFIED:0

The derivation audit refuses both with NOT_AUDITABLE__MULTI_STEP rather than catching the
bad one. The shape audit passes both. The carrier is confined, the workspace is untouched,
the exit code is 0. Every invariant this project can check is satisfied by an answer that is
off by the entire result.

AND THE HONEST ANSWER IS NO BETTER OFF. The correct two-stage pipeline answers 3 and the
auditor says NOT_AUDITABLE__PIPELINE. r48's headline -- 23/23 ANSWER_MATCHES_ITS_SOURCE --
was 23 single-command answers. Multi-step answers have never been auditable, and this is the
first round that asked.

CORROBORATION, 2026. rtk-ai/rtk issue #4091 documents a `wc` that "prints 0 and exits 0,
making it indistinguishable from a real empty file" and calls it a "silent false zero".
D10Scot/Dispatcharr PR #240 documents the general form: `| wc -l` "launders a failure into a
plausible empty answer" because `$?` after a pipeline is the last stage's status. The same
class, in production, the same week. Final-output-only evaluation cannot see it.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K

GOAL = "count the unique lines of"
TRUTH = 3  # z, a, b


def _compile(steps):
    """Compile and return the result WITHOUT asserting: the guard is what is on trial."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    db = str(tmp / "s.sqlite")
    t = tmp / "teach.txt"; t.write_text("z\na\nz\nb\n", encoding="utf-8")
    h = tmp / "hold.txt"; h.write_text("m\nn\nm\n", encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    r = K.compile_and_qualify_skill(
        goal=f"{GOAL} {t}", trace=steps(str(t)), postcondition=None,
        heldout_goal=f"{GOAL} {h}", heldout_cwd=tmp,
        sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                 "contains": "__nope__"}, db_path=db)
    return r, tmp, db


def _build(steps) -> dict:
    """Kept for the record: the PRE-GUARD behaviour, no longer reachable at compile time."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    db = str(tmp / "s.sqlite")
    t = tmp / "teach.txt"; t.write_text("z\na\nz\nb\n", encoding="utf-8")
    h = tmp / "hold.txt"; h.write_text("m\nn\nm\n", encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    trace = steps(str(t))
    r = K.compile_and_qualify_skill(
        goal=f"{GOAL} {t}", trace=trace, postcondition=None,
        heldout_goal=f"{GOAL} {h}", heldout_cwd=tmp,
        sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                 "contains": "__nope__"}, db_path=db)
    assert r.get("pass"), r.get("status")
    f = tmp / "data.txt"; f.write_text("z\na\nz\nb\n", encoding="utf-8")
    got = K.recall_and_execute_workflow(f"{GOAL} {f}", cwd=str(tmp), db_path=db)
    assert got is not None, "recall returned nothing"
    return got


def _two_exec(t):
    return [{"kind": "cli_exec", "layer": "cli_exec", "argv": ["sort", "-u", t]},
            {"kind": "cli_exec", "layer": "cli_exec", "argv": ["wc", "-l"]}]


def _one_pipeline(t):
    return [{"kind": "cli_pipeline", "layer": "cli_pipeline",
             "stages": [["sort", "-u", t], ["wc", "-l"]]}]


def test_two_exec_steps_are_refused_at_compile_time():
    """THE FIX. The trace that produced 0-with-pass is now refused where it is recorded."""
    r, _, _ = _compile(_two_exec)
    assert r.get("pass") is False
    assert r["status"] == "FAIL_CLOSED__MULTI_STEP_CLI_EXEC_IS_NOT_A_PIPELINE"


def test_the_refusal_names_the_reason_so_it_can_be_acted_on():
    r, _, _ = _compile(_two_exec)
    assert "stdin closed" in r["reason"]
    assert r["layers_recorded"] == ["cli_exec", "cli_exec"]


def test_the_carrier_itself_cannot_see_the_problem():
    """Why the refusal had to go in at compile time. `wc -l` on empty stdin prints 0 and
    exits 0 under the real carrier, confined and untouched. That is correct wc behaviour."""
    from canonical.runtime import admitted_confinement_execution_v1 as C
    out = C.execute_confined(["wc", "-l"], workspace_root=tempfile.mkdtemp())
    if out.get("pass") is False and out.get("exit") is None:
        pytest.skip("carrier unavailable in this sandbox; the compile guard is the assertion")
    assert out.get("stdout") == "0\n" or out.get("exit") == 0


def test_the_same_skill_as_one_pipeline_answers_three():
    got = _build(_one_pipeline)
    assert got["answer"] == TRUTH


def test_the_wrong_answer_could_not_be_distinguished_from_a_real_empty_result():
    """A genuinely empty file also gives 0 / STDOUT_INTEGER_VERIFIED:0."""
    tmp = pathlib.Path(tempfile.mkdtemp()); db = str(tmp / "s.sqlite")
    e = tmp / "teach_empty.txt"; e.write_text("", encoding="utf-8")
    h = tmp / "hold.txt"; h.write_text("m\nn\nm\n", encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    K.compile_and_qualify_skill(
        goal=f"count the lines of {e}",
        trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": ["wc", "-l", str(e)]}],
        postcondition=None, heldout_goal=f"count the lines of {h}", heldout_cwd=tmp,
        sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                 "contains": "__nope__"}, db_path=db)
    z = tmp / "zero.txt"; z.write_text("", encoding="utf-8")
    real = K.recall_and_execute_workflow(f"count the lines of {z}", cwd=str(tmp), db_path=db)
    # The shape of the defect, recorded so the guard's value is legible: a real empty file
    # verifies as 0/STDOUT_INTEGER_VERIFIED:0. That is the exact receipt the broken
    # two-step skill produced before the guard existed.
    assert (real["answer"], real["verification_reason"]) == (0, "STDOUT_INTEGER_VERIFIED:0")


def test_the_shape_audit_would_have_passed_the_wrong_answer():
    """A count was asked for and a count came back. The shape audit has no way to know."""
    shape = K.audit_answer_shape(f"count the unique lines of data.txt", {"answer": 0})
    assert shape.get("shape_matches") is True


def test_the_derivation_audit_refuses_a_multi_step_answer():
    """It cannot catch the bad one. Both multi-step answers are simply unauditable."""
    record = {"answer": 0, "provenance": {"steps": [{"argv": ["sort", "-u", "d"]},
                                                    {"argv": ["wc", "-l"]}]}}
    a = K.audit_answer_by_rederivation(record)
    assert a["auditable"] is False
    assert "MULTI_STEP" in a["verdict"]


def test_the_correct_pipeline_answer_is_also_unauditable():
    """r48's 23/23 were all single commands. This is the gap that hid it."""
    got = _build(_one_pipeline)
    assert got["answer"] == TRUTH
    assert K.audit_answer_by_rederivation(got)["verdict"] == "NOT_AUDITABLE__PIPELINE"
