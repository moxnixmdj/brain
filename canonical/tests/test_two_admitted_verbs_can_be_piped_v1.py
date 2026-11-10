"""Composition exists, and it is bounded (r43, 2026-11-09).

WHY THIS EXISTS
---------------
r42 measured the ceiling: 23 read verbs pass one at a time, and NO TWO COULD BE CHAINED
(`cli_pipeline` was refused, and every cli_exec step ran independently). Composition is
the multiplier: 23 verbs in parallel is 23 capabilities; 23 that sequence is thousands.

WHAT WAS BUILT
--------------
`admitted_confinement_execution_v1.execute_pipe_confined(stages)` -- a pipe is
STRUCTURE, not a string. The caller passes [["sort","-u","f"], ["wc","-l"]]. Each stage
goes through the same `admission_verdict` a lone command does, so a pipe can never admit
anything a single command could not. Every argument carrying | & ; > < ` $ ( ) { } is
refused, so no stage can smuggle structural intent inside a scalar. The command string is
built here with `shlex.quote`; the trace never supplies one.

WHAT WAS MEASURED
-----------------
  * 13 malicious shapes -> 13 refusals (semicolon, $(...), backtick, pipe-in-arg,
    redirect, writer program, sh/bash, python3, git, uninstalled, single stage, empty
    stage, and `sort --output=x`).
  * Legitimate pipes run and are CORRECT: `sort -u | wc -l` -> 4 on a 4-unique file.
  * A composite skill taught from ONE pipeline demonstration qualifies (held-out +
    sabotage control) and answers 3 composites out of 4 correctly on a file with
    DIFFERENT contents. The 4th (`nl`) fails honestly because its output is multi-line
    and `stdout_integer` is the wrong postcondition -- it refuses instead of lying.

WHAT THIS DOES NOT SAY
----------------------
It is not "anything on a computer". The pipe is still read-only, still admitted verbs
only, still no writes, no network, no code execution. It raised the ceiling from 23
single verbs to compositions OF THOSE 23 -- a real multiplier, not a general solver.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.runtime import admitted_confinement_execution_v1 as A
from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K

FIXTURE = "zebra\napple\nzebra\nmango\napple\nkiwi\nmango\n"   # 4 unique of 7


def _ws():
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "d.txt").write_text(FIXTURE, encoding="utf-8")
    return tmp


# ---------------------------------------------------------------- safety first
@pytest.mark.parametrize("label,stages", [
    ("semicolon", [["sort", "-u", "d.txt; rm -rf /"], ["wc", "-l"]]),
    ("subst", [["sort", "-u", "$(id)"], ["wc", "-l"]]),
    ("backtick", [["sort", "-u", "`id`"], ["wc", "-l"]]),
    ("pipe-in-arg", [["grep", "a|b", "d.txt"], ["wc", "-l"]]),
    ("redirect", [["sort", "d.txt>pwned"], ["wc", "-l"]]),
    ("writer", [["rm", "-f", "d.txt"], ["wc", "-l"]]),
    ("shell", [["sh", "-c", "id"], ["wc", "-l"]]),
    ("python", [["python3", "-c", "print(1)"], ["wc", "-l"]]),
    ("git", [["git", "status"], ["wc", "-l"]]),
    ("not-installed", [["xxd", "d.txt"], ["wc", "-l"]]),
    ("one-stage", [["sort", "d.txt"]]),
    ("empty-stage", [["sort", "d.txt"], []]),
    ("write-flag-with-value", [["sort", "--output=x", "d.txt"], ["wc", "-l"]]),
])
def test_no_smuggled_structure_ever_passes(label, stages):
    verdict = A.admission_verdict_for_pipe(stages)
    assert verdict["admitted"] is False, f"{label} was admitted: {verdict}"


def test_writes_and_substitution_never_happen():
    ws = _ws()
    out = A.execute_pipe_confined([["sort", "d.txt>pwned"], ["wc", "-l"]],
                                  workspace_root=str(ws))
    assert out["pass"] is False
    assert (ws / "d.txt").exists() and not (ws / "pwned").exists()


# ---------------------------------------------------------------- it works
def test_a_pipe_of_two_admitted_verbs_runs_and_is_correct():
    ws = _ws()
    out = A.execute_pipe_confined([["sort", "-u", "d.txt"], ["wc", "-l"]],
                                  workspace_root=str(ws))
    assert out["pass"] is True, out.get("status")
    assert str(out["stdout"]).strip() == "4"
    assert out["live_workspace_untouched"] is True


def test_three_stages_work():
    ws = _ws()
    out = A.execute_pipe_confined([["sort", "-u", "d.txt"], ["rev"], ["head", "-2"]],
                                  workspace_root=str(ws))
    assert out["pass"] is True, out.get("status")
    # unique lines sorted are apple, kiwi, mango, zebra; after `rev`, head -2 is
    # elppa, iwik. (The first draft of this test expected ognam -- my error, not the
    # code's: `head -2` takes the FIRST two, and mango is third.)
    assert str(out["stdout"]).split() == ["elppa", "iwik"]


def test_the_command_string_is_built_not_supplied():
    """`stages` is structure; there is no path by which a caller hands in a command."""
    verdict = A.admission_verdict_for_pipe([["sort", "-u", "f"], ["wc", "-l"]])
    assert verdict["command"] == "sort -u f | wc -l"


# ------------------------------------------------- the ceiling actually moved
def test_a_composite_skill_is_learned_from_one_pipeline_demonstration():
    """r42: this exact shape qualified then answered 1 for 3. It must now be right."""
    root = pathlib.Path(tempfile.mkdtemp())
    db = str(root / "s.sqlite")
    t = root / "t.txt"; t.write_text(FIXTURE, encoding="utf-8")
    h = root / "h.txt"; h.write_text("kiwi\nplum\nkiwi\nfig\nplum\nkiwi\norange\n",
                                     encoding="utf-8")        # 4 unique, 6 lines
    s = root / "s.txt"; s.write_text("x\n", encoding="utf-8")
    r = K.compile_and_qualify_skill(
        goal=f"count the unique lines of {t}",
        trace=[{"kind": "cli_pipeline", "layer": "cli_pipeline",
                "stages": [["sort", "-u", str(t)], ["wc", "-l"]]}],
        postcondition={"kind": "stdout_integer"},
        heldout_goal=f"count the unique lines of {h}",
        heldout_cwd=root,
        sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                 "contains": "__nope__"},
        db_path=db,
    )
    assert r.get("pass"), r.get("status")
    hit = K.recall_and_execute_workflow(f"count the unique lines of {h}",
                                        cwd=str(root), db_path=db)
    assert hit is not None
    assert hit.get("answer") == 4, hit


def test_a_wrong_postcondition_refuses_instead_of_lying():
    """`nl` prints several lines, so stdout_integer is the wrong check. It must refuse."""
    root = pathlib.Path(tempfile.mkdtemp())
    db = str(root / "s.sqlite")
    t = root / "t.txt"; t.write_text(FIXTURE, encoding="utf-8")
    h = root / "h.txt"; h.write_text(FIXTURE, encoding="utf-8")
    s = root / "s.txt"; s.write_text("x\n", encoding="utf-8")
    r = K.compile_and_qualify_skill(
        goal=f"count the numbered unique lines of {t}",
        trace=[{"kind": "cli_pipeline", "layer": "cli_pipeline",
                "stages": [["sort", "-u", str(t)], ["nl", "-ba"]]}],
        postcondition={"kind": "stdout_integer"},
        heldout_goal=f"count the numbered unique lines of {h}",
        heldout_cwd=root,
        sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                 "contains": "__nope__"},
        db_path=db,
    )
    assert not r.get("pass"), "a multi-line output must not satisfy stdout_integer"
